import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    # 1. Initialize a secure database connection layer pointing to MotherDuck
    # It automatically picks up the tokens we updated in your system environment!
    con = duckdb.connect("md:")

    # 2. Add an interactive UI slider component right into your notebook canvas
    # This showcases Marimo's native reactive UI rendering engine
    limit_slider = mo.ui.slider(start=10, stop=100, step=5, value=25, label="Records to View")
    limit_slider
    return


if __name__ == "__main__":
    app.run()
