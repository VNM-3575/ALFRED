# Imports AFANDE_SYSTEM_PROMPTS

# agents/afande.py
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.prompts import AFANDE_SYSTEM_PROMPT  # Import from your config file


def run_afande_agent(user_task: str):
    # 1. Initialize the LLM
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1)

    # 2. Format the message array explicitly separating System Identity from User Request
    messages = [
        SystemMessage(content=AFANDE_SYSTEM_PROMPT),
        HumanMessage(content=user_task)
    ]

    # 3. Fire the API Call
    response = llm.invoke(messages)
    return response.content
