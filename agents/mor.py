# IMPORT mor_system_prompt

# agents/mor.py
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.prompts import MOR_SYSTEM_PROMPT
# We import MOR's exclusive data tools from our tools directory
from tools.finance_tools import calculate_rsi, query_duckdb

# 1. Initialize MOR's Model (Low temperature for mathematical precision)
mor_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1)

# 2. Bind MOR's exclusive tools
mor_tools = [calculate_rsi, query_duckdb]
mor_llm_with_tools = mor_llm.bind_tools(mor_tools)


def run_mor_agent(state):
    """Execution node for MOR within LangGraph"""
    messages = state["messages"]

    # Prepend MOR's specific identity constraints
    formatted_messages = [SystemMessage(content=MOR_SYSTEM_PROMPT)] + messages

    # Invoke the model to decide if it needs to compute tools or reply
    response = mor_llm_with_tools.invoke(formatted_messages)

    return {
        "messages": [response],
        "active_agent": "MOR"
    }
