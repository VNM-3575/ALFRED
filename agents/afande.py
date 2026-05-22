# Imports AFANDE_SYSTEM_PROMPTS

# agents/afande.py
from langchain_core.messages import SystemMessage, HumanMessage
from config.prompts import AFANDE_SYSTEM_PROMPT  # Import from your config file
from config.llm_config import get_llm


def run_afande_agent(user_task: str):
    # 1. Initialize the LLM dynamically
    llm = get_llm(temperature=0.1)

    # 2. Format the message array explicitly separating System Identity from User Request
    messages = [
        SystemMessage(content=AFANDE_SYSTEM_PROMPT),
        HumanMessage(content=user_task)
    ]

    # 3. Fire the API Call
    response = llm.invoke(messages)
    return response.content
