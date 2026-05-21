import duckdb
import yfinance as yf
import pandas_ta as ta
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
def calculate_rsi(ticker: str, period: int = 14) -> str:
    """
    Calculates the Relative Strength Index (RSI) for a given stock ticker.
    """
    try:
        # Fetch historical market data (fetch 3x period to ensure RSI has enough data to "warm up")
        data = yf.Ticker(ticker).history(period=f"{period * 3}d")
        if data.empty:
            return f"Could not fetch data for ticker {ticker}."

        # Calculate RSI using pandas-ta and grab the latest value
        data.ta.rsi(length=period, append=True)
        latest_rsi = data[f"RSI_{period}"].iloc[-1]
        return f"The current {period}-day RSI for {ticker} is {latest_rsi:.2f}"
    except Exception as e:
        return f"Error calculating RSI: {str(e)}"
