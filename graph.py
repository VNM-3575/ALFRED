
# graph.py
import os
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv

# 1. LangGraph Core Imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, SystemMessage

from config.llm_config import get_llm

# 3. Local Agent Brain Imports
from agents.afande import run_afande_agent
from agents.data_analyst import run_data_analyst_agent
from agents.content_creator import run_content_creator_agent
from agents.student import run_student_agent

# 4. Local Tool Imports (Exposing the exclusive software capabilities)
from tools.security_tools import download_portal_assignment, run_nmap_audit, get_allowed_account_credentials, generic_openclaw_scrape, draft_portal_submission, extract_grading_rubric
from tools.finance_tools import calculate_rsi, query_duckdb, check_openai_balance
from tools.data_engines import download_hf_dataset, load_hf_dataset_to_duckdb, summarize_large_dataset, save_text_to_duckdb
from tools.creative_tools import generate_veo_video, generate_banana_art
from tools.report_tools import generate_pdf_report, generate_chart, update_capabilities_file, publish_to_tableau
from tools.system_tools import write_to_file, request_shell_execution
from tools.audio_tools import transcribe_audio
from tools.social_tools import post_to_social_media, make_web_request
from tools.vision_tools import record_screen

load_dotenv()

# =====================================================================
# 📊 1. DEFINING THE GLOBAL RESOURCE (THE GRAPH STATE)
# =====================================================================


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The history of the conversation"]
    # Tracks who currently has control (ALFRED, AFANDE, DATA_ANALYST, CONTENT_CREATOR, STUDENT)
    active_agent: str
    shared_notes: str  # A global scratchpad for agents to share raw data configurations


# =====================================================================
# 🧠 2. ALFRED'S CORE ORCHESTRATION LOGIC & SYSTEM PROMPT
# =====================================================================
ALFRED_SYSTEM_PROMPT = """You are ALFRED (Advanced Logical Functional Retrieval & Execution Director). 
Your job is to read user goals and delegate tasks to your specialized sub-agents:
- AFANDE: ALFRED's system hands. For local file writing, web requests, web portal access (OpenClaw), and social media.
- DATA_ANALYST: For processing scraped web data, data science, DuckDB/PostgreSQL pipelines, and math.
- CONTENT_CREATOR: For data summaries, Tableau operations, video/image generation, audio transcription, and writing PDF reports.
- STUDENT: For orchestrating web scraping logins from 'allowed-access-accounts', analyzing pages, and managing submissions.

When you identify system improvements, new automation ideas (like cron jobs), or git review/commit/push sequences, actively suggest them and instruct AFANDE to append them to 'data/suggestions.md' using file tools.
When new capabilities or tools are added to the system, instruct the CONTENT_CREATOR to update the 'data/capabilities.md' file.

CRITICAL: You are the director. Speak directly to the user or call upon an agent by updating the active_agent tracking status. Do not try to perform specialized tasks yourself."""

alfred_llm = get_llm(temperature=0.2)


def alfred_director(state: AgentState):
    """ALFRED evaluates the state and decides who should work next"""
    messages = [SystemMessage(
        content=ALFRED_SYSTEM_PROMPT)] + state["messages"]
    response = alfred_llm.invoke(messages)

    # We let ALFRED's response determine if he's routing or answering the user directly
    return {
        "messages": [response],
        "active_agent": "ALFRED"
    }


# =====================================================================
# 🚦 3. EXPOSING AND ROUTING THE TOOLS
# =====================================================================
# Group tools by agent to keep capabilities completely exclusive
afande_tools = [download_portal_assignment,
                run_nmap_audit, write_to_file, request_shell_execution,
                post_to_social_media, make_web_request, generic_openclaw_scrape, record_screen]
data_analyst_tools = [calculate_rsi, query_duckdb, check_openai_balance,
                      download_hf_dataset, load_hf_dataset_to_duckdb, save_text_to_duckdb]

content_creator_tools = [generate_veo_video, generate_banana_art, generate_pdf_report, generate_chart,
                         transcribe_audio, summarize_large_dataset, update_capabilities_file, publish_to_tableau]
student_tools = [get_allowed_account_credentials,
                 draft_portal_submission, extract_grading_rubric]

# Combine all tools into a single execution node for LangGraph to reference
all_project_tools = afande_tools + data_analyst_tools + \
    content_creator_tools + student_tools
tool_node = ToolNode(all_project_tools)

# =====================================================================
# 🛠️ 4. BUILDING THE STATE GRAPH WORKFLOW
# =====================================================================
workflow = StateGraph(AgentState)

# Add our processing blocks (Nodes)
workflow.add_node("ALFRED", alfred_director)
workflow.add_node("AFANDE", run_afande_agent)
workflow.add_node("DATA_ANALYST", run_data_analyst_agent)
workflow.add_node("CONTENT_CREATOR", run_content_creator_agent)
workflow.add_node("STUDENT", run_student_agent)
workflow.add_node("tools", tool_node)

# Set the entry point where every user interaction starts
workflow.set_entry_point("ALFRED")

# Define the Routing Rules (Conditional Edges)


def route_after_alfred(state: AgentState):
    """ALFRED analyzes his own output text to route to the correct sub-agent"""
    last_message = state["messages"][-1].content.lower()

    if "afande" in last_message:
        return "AFANDE"
    elif "data_analyst" in last_message or "data analyst" in last_message:
        return "DATA_ANALYST"
    elif "content_creator" in last_message or "content creator" in last_message:
        return "CONTENT_CREATOR"
    elif "student" in last_message:
        return "STUDENT"
    else:
        # If ALFRED answers the user directly without naming an agent, stop.
        return END


def route_after_agent(state: AgentState):
    """Sub-agents check if they emitted a tool call. If so, go to tools node. If not, go back to ALFRED."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "ALFRED"


def route_after_tools(state: AgentState):
    """Once an external API tool finishes executing, return to the agent who called it"""
    current_worker = state["active_agent"]
    return current_worker


# Attach the routing logic into the graph grid layout
workflow.add_conditional_edges("ALFRED", route_after_alfred)
workflow.add_conditional_edges("AFANDE", route_after_agent)
workflow.add_conditional_edges("DATA_ANALYST", route_after_agent)
workflow.add_conditional_edges("CONTENT_CREATOR", route_after_agent)
workflow.add_conditional_edges("STUDENT", route_after_agent)
workflow.add_conditional_edges("tools", route_after_tools)

# Compile everything into an executable runtime application object
alfred_app = workflow.compile()
