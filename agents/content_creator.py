from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.system_prompts import AGENT_CONTENT_CREATOR_PROMPT

from tools.creative_tools import generate_veo_video, generate_banana_art
from tools.report_tools import generate_pdf_report, generate_chart, update_capabilities_file
from tools.audio_tools import transcribe_audio
from tools.data_engines import summarize_large_dataset

# 1. Initialize Model
content_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)

# 2. Bind Tools
content_tools = [generate_veo_video, generate_banana_art,
                 generate_pdf_report, generate_chart, transcribe_audio, summarize_large_dataset, update_capabilities_file]
content_llm_with_tools = content_llm.bind_tools(content_tools)


def run_content_creator_agent(state):
    messages = state["messages"]
    formatted_messages = [SystemMessage(
        content=AGENT_CONTENT_CREATOR_PROMPT)] + messages
    response = content_llm_with_tools.invoke(formatted_messages)
    return {"messages": [response], "active_agent": "CONTENT_CREATOR"}
