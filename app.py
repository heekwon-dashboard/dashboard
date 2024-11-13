import dash
from dash import html

# Initialize the Dash application
app = dash.Dash(__name__)

# Define the layout
app.layout = html.Div("Hello, World!")

# Run the app locally (only if not running with Gunicorn)
if __name__ == "__main__":
    app.run_server(debug=True)
