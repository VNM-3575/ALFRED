from config.llm_config import get_llm
import os
import glob
import duckdb
import sys
from pypdf import PdfReader
from langchain_core.messages import HumanMessage

# Add project root to the system path so we can import ALFRED's config modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def summarize_pdfs_to_duckdb(data_dir="data", db_path="data/local_warehouse.duckdb", table_name="pdf_summaries"):
    """Reads all PDFs in the data directory, summarizes them via LLM, and stores them in DuckDB."""
    print("📄 =========================================")
    print("📄 ALFRED: PDF Summarization to DuckDB Workflow")
    print("📄 =========================================\n")

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in the '{data_dir}' directory.")
        return

    print(f"Found {len(pdf_files)} PDF(s). Initializing LLM and DuckDB...")

    llm = get_llm(temperature=0.2)
    con = duckdb.connect(db_path)

    # Create the destination table if it does not already exist
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id VARCHAR DEFAULT uuid(),
            filename VARCHAR,
            summary TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        print(f"\nProcessing: {filename}")

        try:
            reader = PdfReader(pdf_file)
            text = "".join(page.extract_text() +
                           "\n" for page in reader.pages if page.extract_text())

            if not text.strip():
                print(f"  -> Skipping {filename}: No readable text found.")
                continue

            # Truncate text to roughly fit in the context window (first ~30k chars)
            text_preview = text[:30000]
            prompt = f"Please provide a comprehensive summary of the following document. Extract the main purpose, key findings, and any conclusions:\n\n{text_preview}"

            print("  -> Generating summary...")
            response = llm.invoke([HumanMessage(content=prompt)])
            summary = response.content

            print("  -> Saving to DuckDB...")
            con.execute(
                f"INSERT INTO {table_name} (filename, summary) VALUES (?, ?)", (filename, summary))
            print(f"  ✅ Saved summary for {filename}")

        except Exception as e:
            print(f"  ❌ Failed to process {filename}: {str(e)}")

    con.close()
    print("\n🎉 Workflow complete! All summaries have been extracted and stored in DuckDB.")


if __name__ == "__main__":
    summarize_pdfs_to_duckdb()
