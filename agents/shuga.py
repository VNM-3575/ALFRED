# Imports SHUGA_SYSTEM_PROMPTS

# agents/shuga.py
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.prompts import SHUGA_SYSTEM_PROMPT
# We import SHUGA's exclusive media tools
from tools.creative_tools import generate_veo_video, generate_banana_art

# 1. Initialize SHUGA's Model (Higher temperature for creative variance)
gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
shuga_llm = ChatGoogleGenerativeAI(model=gemini_model, temperature=0.7)

# 2. Bind SHUGA's exclusive tools
shuga_tools = [generate_veo_video, generate_banana_art]
shuga_llm_with_tools = shuga_llm.bind_tools(shuga_tools)


def run_shuga_agent(state):
    """Execution node for SHUGA&SPICE within LangGraph"""
    messages = state["messages"]

    formatted_messages = [SystemMessage(
        content=SHUGA_SYSTEM_PROMPT)] + messages
    response = shuga_llm_with_tools.invoke(formatted_messages)

    return {
        "messages": [response],
        "active_agent": "SHUGA&SPICE"
    }
