import os
import requests
import psycopg2
import duckdb
from langchain_core.tools import tool


@tool
def run_pipeline_diagnostics() -> str:
    """
    DOCTOR TOOL: Runs a full diagnostic check on the ALFRED pipeline, schema, database connections, and environment variables.
    Returns a health report with Issue IDs for any detected problems.
    """
    report = ["🏥 ALFRED Pipeline Diagnostic Report:\n"]
    issues_found = []

    # 1. Environment Variables
    keys = ["GOOGLE_API_KEY", "OPENAI_API_KEY",
            "OPENCLAW_API_URL", "DATABASE_URL"]
    for key in keys:
        if not os.getenv(key):
            report.append(f"❌ Missing Env Var: {key}")
            issues_found.append(f"MISSING_ENV_{key}")
        else:
            report.append(f"✅ Env Var Present: {key}")

    # 2. PostgreSQL Connection
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://alfred_admin:alfred_password@localhost:5432/alfred_warehouse")
    db_url = db_url.replace("@db:5432", "@localhost:5432")
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        report.append("✅ PostgreSQL Database: Connected")
    except Exception as e:
        report.append(f"❌ PostgreSQL Database: Disconnected ({str(e)})")
        issues_found.append("DB_CONNECTION_FAILED")

    # 3. DuckDB File Access
    try:
        os.makedirs("data", exist_ok=True)
        con = duckdb.connect("data/local_warehouse.duckdb")
        con.close()
        report.append("✅ DuckDB Workspace: Accessible")
    except Exception as e:
        report.append(f"❌ DuckDB Workspace: Failed ({str(e)})")
        issues_found.append("DUCKDB_ACCESS_FAILED")

    # 4. Folder Structure
    required_folders = ["data", "allowed-access-accounts", "data/hf_datasets"]
    for folder in required_folders:
        if os.path.exists(folder):
            report.append(f"✅ Directory Exists: {folder}/")
        else:
            report.append(f"❌ Missing Directory: {folder}/")
            issues_found.append(
                f"MISSING_DIR_{folder.replace('/', '_').upper()}")

    # 5. OpenClaw API Responsiveness
    openclaw_url = os.getenv(
        "OPENCLAW_API_URL", "http://localhost:8000/api/automate")
    try:
        # A simple GET request to check if the server is reachable
        requests.get(openclaw_url, timeout=5)
        report.append("✅ OpenClaw API: Responsive")
    except requests.exceptions.RequestException as e:
        report.append(f"❌ OpenClaw API: Unresponsive ({type(e).__name__})")
        issues_found.append("OPENCLAW_UNRESPONSIVE")

    if not issues_found:
        report.append("\n🎉 Pipeline is 100% Healthy!")
    else:
        report.append(f"\n⚠️ Issues Detected: {', '.join(issues_found)}")
        report.append(
            "Use the 'apply_pipeline_fix' tool (DOCTOR-FIX) with the specific Issue ID to attempt auto-remediation.")

    return "\n".join(report)


@tool
def apply_pipeline_fix(issue_id: str) -> str:
    """
    DOCTOR-FIX TOOL: Attempts to automatically remediate a specific issue identified by run_pipeline_diagnostics.
    """
    if issue_id.startswith("MISSING_DIR_"):
        folder_name = issue_id.replace(
            "MISSING_DIR_", "").replace("_", "/").lower()
        # Account for specific folder naming anomalies
        if folder_name == "allowed/access/accounts":
            folder_name = "allowed-access-accounts"
        elif folder_name == "data/hf/datasets":
            folder_name = "data/hf_datasets"

        os.makedirs(folder_name, exist_ok=True)
        return f"✅ DOCTOR-FIX: Successfully created missing directory '{folder_name}'."

    elif issue_id.startswith("MISSING_ENV_"):
        var_name = issue_id.replace("MISSING_ENV_", "")
        return f"⚠️ DOCTOR-FIX: Cannot auto-generate API keys for '{var_name}'. Please add it to the .env file or Streamlit UI."

    elif issue_id == "DB_CONNECTION_FAILED":
        return "⚠️ DOCTOR-FIX: Cannot auto-start PostgreSQL from inside the agent. Please ensure Docker Compose is running (`docker-compose up -d db`)."

    elif issue_id == "DUCKDB_ACCESS_FAILED":
        try:
            os.makedirs("data", exist_ok=True)
            duckdb.connect("data/local_warehouse.duckdb").close()
            return "✅ DOCTOR-FIX: DuckDB workspace initialized and file permissions reset."
        except Exception as e:
            return f"❌ DOCTOR-FIX: Failed to reset DuckDB - {str(e)}"

    elif issue_id == "OPENCLAW_UNRESPONSIVE":
        return "⚠️ DOCTOR-FIX: Cannot auto-start OpenClaw remotely. Please verify your ngrok tunnel is active or your OpenClaw container is running."

    return f"❌ DOCTOR-FIX: Unknown or unfixable Issue ID '{issue_id}'."
