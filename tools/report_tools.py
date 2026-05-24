import os
import json
import matplotlib.pyplot as plt
from fpdf import FPDF
import tableauserverclient as TSC
from langchain_core.tools import tool


@tool
def generate_pdf_report(content: str, filename: str = "report.pdf") -> str:
    """
    Generates a PDF report from the provided text content and saves it to the data/ directory.
    Useful for converting data summaries and creative writing into a final downloadable PDF.
    """
    try:
        filepath = os.path.join("data", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        # Standard PDF fonts expect latin-1; we safely ignore complex unicode (like emojis) to prevent crashes
        safe_content = content.encode('latin-1', 'ignore').decode('latin-1')

        pdf.multi_cell(0, 10, text=safe_content)
        pdf.output(filepath)
        return f"Successfully generated PDF report and saved to {filepath}"
    except Exception as e:
        return f"Failed to generate PDF report: {str(e)}"


@tool
def generate_chart(chart_type: str, labels: str, values: str, title: str, filename: str = "chart.png") -> str:
    """
    Generates a chart (bar, pie, or line) and saves it as an image in the data/ directory.
    chart_type: 'bar', 'pie', or 'line'.
    labels: A JSON string list of categories (e.g., '["Positive", "Negative"]').
    values: A JSON string list of numerical values (e.g., '[50, 30]').
    """
    try:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)

        lbls = json.loads(labels)
        vals = json.loads(values)

        plt.figure(figsize=(8, 6))
        if chart_type.lower() == "bar":
            plt.bar(lbls, vals, color='skyblue')
        elif chart_type.lower() == "pie":
            plt.pie(vals, labels=lbls, autopct='%1.1f%%', startangle=140)
        elif chart_type.lower() == "line":
            plt.plot(lbls, vals, marker='o', linestyle='-')
        else:
            return f"Unsupported chart type: {chart_type}. Use 'bar', 'pie', or 'line'."

        plt.title(title)
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()

        return f"Successfully generated {chart_type} chart and saved to {filepath}"
    except Exception as e:
        return f"Failed to generate chart: {str(e)}"


@tool
def update_capabilities_file(new_markdown_content: str) -> str:
    """
    Overwrites the data/capabilities.md file with the provided markdown content.
    Use this to update the list of agent capabilities whenever a new tool is added.
    """
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/capabilities.md", "w", encoding="utf-8") as f:
            f.write(new_markdown_content)
        return "Successfully updated data/capabilities.md"
    except Exception as e:
        return f"Failed to update capabilities: {str(e)}"


@tool
def publish_to_tableau(project_name: str, file_path: str) -> str:
    """
    Publishes a data source or workbook (.tds, .tdsx, .twb, .twbx) to Tableau Server/Cloud.
    Requires TABLEAU_SERVER, TABLEAU_TOKEN_NAME, TABLEAU_TOKEN_VALUE, and TABLEAU_SITE_ID environment variables.
    """
    try:
        server_url = os.getenv("TABLEAU_SERVER")
        token_name = os.getenv("TABLEAU_TOKEN_NAME")
        token_value = os.getenv("TABLEAU_TOKEN_VALUE")
        site_id = os.getenv("TABLEAU_SITE_ID", "")

        if not all([server_url, token_name, token_value]):
            return "Missing Tableau environment variables. Please configure TABLEAU_SERVER, TABLEAU_TOKEN_NAME, and TABLEAU_TOKEN_VALUE."

        tableau_auth = TSC.PersonalAccessTokenAuth(
            token_name, token_value, site_id=site_id)
        server = TSC.Server(server_url, use_server_version=True)

        with server.auth.sign_in(tableau_auth):
            # Find project by name
            req_option = TSC.RequestOptions()
            req_option.filter.add(TSC.Filter(
                TSC.RequestOptions.Field.Name, TSC.RequestOptions.Operator.Equals, project_name))
            all_projects, _ = server.projects.get(req_option)

            if not all_projects:
                return f"Tableau project '{project_name}' not found."

            project_id = all_projects[0].id

            if file_path.endswith(('.twb', '.twbx')):
                new_workbook = TSC.WorkbookItem(project_id)
                new_workbook = server.workbooks.publish(
                    new_workbook, file_path, 'Overwrite')
                return f"Successfully published workbook '{new_workbook.name}' to Tableau."
            elif file_path.endswith(('.tds', '.tdsx', '.hyper')):
                new_datasource = TSC.DatasourceItem(project_id)
                new_datasource = server.datasources.publish(
                    new_datasource, file_path, 'Overwrite')
                return f"Successfully published datasource '{new_datasource.name}' to Tableau."
            else:
                return "Unsupported file type. Tableau publishing requires .twb, .twbx, .tds, .tdsx, or .hyper."

    except Exception as e:
        return f"Failed to publish to Tableau: {str(e)}"
