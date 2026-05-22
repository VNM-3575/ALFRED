from langchain_core.messages import SystemMessage
from config.system_prompts import AGENT_DATA_ANALYST_PROMPT
from config.llm_config import get_llm

from tools.finance_tools import calculate_rsi, query_duckdb
from tools.data_engines import download_hf_dataset, load_hf_dataset_to_duckdb, save_text_to_duckdb

# 1. Initialize Model (Lower temperature for analytical precision)
analyst_llm = get_llm(temperature=0.1)

# 2. Bind Tools
analyst_tools = [calculate_rsi, query_duckdb,
                 download_hf_dataset, load_hf_dataset_to_duckdb, save_text_to_duckdb]
analyst_llm_with_tools = analyst_llm.bind_tools(analyst_tools)


def run_data_analyst_agent(state):
    messages = state["messages"]
    formatted_messages = [SystemMessage(
        content=AGENT_DATA_ANALYST_PROMPT)] + messages
    response = analyst_llm_with_tools.invoke(formatted_messages)
    return {"messages": [response], "active_agent": "DATA_ANALYST"}
