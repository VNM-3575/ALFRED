from langchain_core.messages import SystemMessage
from config.system_prompts import AGENT_STUDENT_PROMPT
from tools.security_tools import get_allowed_account_credentials
from config.llm_config import get_llm

student_llm = get_llm(temperature=0.3)

# Bind the credentials reading tool to the STUDENT agent
student_tools = [get_allowed_account_credentials]
student_llm_with_tools = student_llm.bind_tools(student_tools)

# The STUDENT agent acts as a sub-orchestrator. It formulates scraping logic and
# instructs ALFRED to execute it via OpenClaw, rather than running the tool directly.


def run_student_agent(state):
    messages = state["messages"]
    formatted_messages = [SystemMessage(
        content=AGENT_STUDENT_PROMPT)] + messages

    response = student_llm_with_tools.invoke(formatted_messages)

    return {"messages": [response], "active_agent": "STUDENT"}
