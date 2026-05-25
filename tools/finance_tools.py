import os
import requests
from datetime import datetime, timedelta
import duckdb
import yfinance as yf
import psycopg2
import ta
import pandas as pd
from langchain_core.tools import tool


@tool
def query_duckdb(query: str) -> str:
    """
    Executes a SQL query against the local DuckDB instance and returns the results.
    Useful for data analysis, financial aggregations, and tabular operations.
    """
    try:
        # Connect to a local file-based DuckDB database inside the data directory
        # If the file doesn't exist, DuckDB will create it automatically.
        con = duckdb.connect("data/local_warehouse.duckdb")

        # Configure memory limits to prevent out-of-memory errors on large datasets
        con.execute("PRAGMA memory_limit='4GB'")

        # Execute query and limit results to prevent LLM context overflow and RAM spikes
        # con.sql() allows us to chain .limit() before evaluating to a pandas DataFrame
        df = con.sql(query).limit(100).df()
        con.close()

        # Return string representation of the DataFrame for the LLM to read
        if df.empty:
            return "Query executed successfully, but no data was returned."
        return df.to_string()
    except Exception as e:
        return f"Error executing DuckDB query: {str(e)}"


@tool
def query_postgresql(query: str) -> str:
    """
    Executes a SQL query against the PostgreSQL data warehouse and returns the results.
    Useful for querying system logs, active tasks, and other relational data.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "Error: DATABASE_URL environment variable is missing."

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description is None:
                    return "Query executed successfully (no rows returned)."

                columns = [desc[0] for desc in cur.description]
                # Limit to 100 rows to prevent context window overflow
                rows = cur.fetchmany(100)
                if not rows:
                    return "Query executed successfully, but no data was returned."

                df = pd.DataFrame(rows, columns=columns)
                return df.to_string()
    except Exception as e:
        return f"Error executing PostgreSQL query: {str(e)}"


@tool
def calculate_rsi(ticker: str, period: int = 14) -> str:
    """
    Calculates the Relative Strength Index (RSI) for a given stock ticker.
    """
    try:
        # Fetch historical market data (fetch 3x period to ensure RSI has enough data to "warm up")
        data = yf.Ticker(ticker).history(period=f"{period * 3}d")
        if data.empty:
            return f"Could not fetch data for ticker {ticker}."

        # Calculate RSI using the 'ta' library and grab the latest value
        rsi_series = ta.momentum.RSIIndicator(
            data['Close'], window=period).rsi()
        latest_rsi = rsi_series.iloc[-1]
        return f"The current {period}-day RSI for {ticker} is {latest_rsi:.2f}"
    except Exception as e:
        return f"Error calculating RSI: {str(e)}"


@tool
def check_openai_balance() -> str:
    """
    Checks the current OpenAI API usage and balance for the active API key.
    Returns the hard limit and the total usage for the current calendar month.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY environment variable is missing."

    headers = {"Authorization": f"Bearer {api_key}"}
    base_url = "https://api.openai.com/v1/dashboard/billing"

    try:
        # Calculate start and end dates for the current calendar month
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Fetch subscription limit
        sub_res = requests.get(
            f"{base_url}/subscription", headers=headers, timeout=10)
        sub_res.raise_for_status()
        hard_limit = sub_res.json().get("hard_limit_usd", 0.0)

        # Fetch monthly usage
        usage_res = requests.get(
            f"{base_url}/usage?start_date={start_date}&end_date={end_date}", headers=headers, timeout=10)
        usage_res.raise_for_status()
        total_usage = usage_res.json().get("total_usage", 0.0) / \
            100.0  # API returns usage in cents

        return f"OpenAI API Balance:\n- Usage this month: ${total_usage:.2f}\n- Hard Limit: ${hard_limit:.2f}"
    except requests.exceptions.RequestException as e:
        return f"Failed to fetch OpenAI balance. Note: OpenAI frequently restricts billing endpoints for standard API keys (403 Forbidden). Error: {str(e)}"
