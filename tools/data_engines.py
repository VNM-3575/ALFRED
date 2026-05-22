# DuckDB local workspace queries
import os
import glob
import duckdb
from huggingface_hub import snapshot_download
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from config.llm_config import get_llm


@tool
def download_hf_dataset(repo_id: str) -> str:
    """
    Downloads a dataset repository from HuggingFace Hub to the local 'data/' directory.
    Useful for pulling data for analysis or model training.
    """
    try:
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        local_dir = os.path.join(
            "data", "hf_datasets", repo_id.replace("/", "_"))
        os.makedirs(local_dir, exist_ok=True)

        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=local_dir,
            token=hf_token
        )
        return f"Successfully downloaded HuggingFace dataset '{repo_id}' to {local_dir}"
    except Exception as e:
        return f"Failed to download HuggingFace dataset '{repo_id}': {str(e)}"


@tool
def load_hf_dataset_to_duckdb(local_dir: str, table_name: str) -> str:
    """
    Loads a locally downloaded HuggingFace dataset into the DuckDB data warehouse.
    Supports datasets containing .parquet or .csv files.
    """
    try:
        con = duckdb.connect("data/local_warehouse.duckdb")

        # Configure DuckDB for out-of-core (larger than RAM) processing
        os.makedirs("data/tmp", exist_ok=True)
        # Adjust limit based on available RAM
        con.execute("PRAGMA memory_limit='4GB'")
        con.execute("PRAGMA temp_directory='data/tmp'")  # Enable disk spilling

        # Detect file type and load accordingly using DuckDB's globbing support
        if glob.glob(f"{local_dir}/**/*.parquet", recursive=True):
            query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{local_dir}/**/*.parquet')"
        elif glob.glob(f"{local_dir}/**/*.csv", recursive=True) or glob.glob(f"{local_dir}/**/*.csv.gz", recursive=True):
            # read_csv_auto automatically handles headers, delimiters, and gzip compression
            query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{local_dir}/**/*.csv*')"
        else:
            con.close()
            return f"No .parquet or .csv files found in the dataset directory: {local_dir}"

        con.execute(query)
        con.close()
        return f"Successfully loaded dataset from {local_dir} into DuckDB table '{table_name}'."
    except Exception as e:
        return f"Failed to load dataset into DuckDB: {str(e)}"


@tool
def summarize_large_dataset(query: str, chunk_size: int = 500, max_chunks: int = 10, generate_pdf: bool = False) -> str:
    """
    Summarizes a large dataset using an LLM MapReduce approach.
    Executes a DuckDB query, reads data in chunks (Map), and synthesizes a final summary (Reduce).
    Use this when a dataset is too large to fit in the LLM's context window.
    """
    try:
        con = duckdb.connect("data/local_warehouse.duckdb")
        con.execute("PRAGMA memory_limit='4GB'")

        # Execute query but do not fetch all data into memory at once
        result = con.execute(query)

        # Using gemini-1.5-flash for map-reduce is faster and cheaper for bulk data tasks
        llm = get_llm(temperature=0.1)
        chunk_summaries = []

        while True:
            df_chunk = result.fetch_df_chunk(chunk_size)
            if df_chunk.empty:
                break

            # --- MAP PHASE ---
            chunk_str = df_chunk.to_csv(index=False)
            map_prompt = f"Identify the key trends, anomalies, and insights in this data chunk:\n\n{chunk_str}"
            response = llm.invoke([HumanMessage(content=map_prompt)])
            chunk_summaries.append(response.content)

            # Safety limit to prevent runaway API requests
            if len(chunk_summaries) >= max_chunks:
                chunk_summaries.append(
                    f"... (Truncated at {max_chunks} chunks to save API resources) ...")
                break

        con.close()

        if not chunk_summaries:
            return "The query returned no data to summarize."

        # --- REDUCE PHASE ---
        combined_summaries = "\n\n---\n\n".join(chunk_summaries)
        reduce_prompt = f"I have provided summaries for several chunks of a large dataset. Combine them into a single, cohesive, comprehensive final summary report:\n\n{combined_summaries}"

        final_response = llm.invoke([
            SystemMessage(
                content="You are an expert data analyst and statistician."),
            HumanMessage(content=reduce_prompt)
        ])

        final_summary = f"📊 MapReduce Final Summary:\n\n{final_response.content}"

        if generate_pdf:
            final_summary += "\n\n[SYSTEM DIRECTIVE: The user requested a PDF report. ALFRED, please route this exact summary to SHUGA and instruct them to use the 'generate_pdf_report' tool to create a PDF.]"

        return final_summary

    except Exception as e:
        return f"Failed to execute MapReduce summarization: {str(e)}"


@tool
def save_text_to_duckdb(table_name: str, text_content: str, source: str = "general") -> str:
    """
    Saves text content (like sentiment analysis results or summaries) into a DuckDB table.
    Creates the table dynamically if it does not exist.
    """
    try:
        con = duckdb.connect("data/local_warehouse.duckdb")

        # Create a flexible table for unstructured analysis
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} (id VARCHAR DEFAULT uuid(), source VARCHAR, content TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        con.execute(
            f"INSERT INTO {table_name} (source, content) VALUES (?, ?)", (source, text_content))
        con.close()
        return f"Successfully saved text to DuckDB table '{table_name}'."
    except Exception as e:
        return f"Failed to save text to DuckDB: {str(e)}"
