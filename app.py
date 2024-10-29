from dash import Dash, html, dcc, callback, Output, Input, State, no_update
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain.load import dumps, loads

import dash_ag_grid as dag
import pandas as pd
import base64
import io
import re

# Groq API Key
GROQ_API_KEY = 'ur key'

# Initialize the Dash app
app = Dash(__name__)
app.title = "Plotly AI Graph Builder Dashboard"

# Initialize the model and prompt
model = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama3-70b-8192",
    # model="Mixtral-8x7b-32768" # Optional model
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "You're a data visualization expert and only use Plotly. The data is in a honey_US.csv file. "
         "Here are the first 5 rows: {data} Follow the user's instructions when creating the graph."),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
    ]
)

chain = prompt | model

# Extract Plotly fig object from the generated code
def get_fig_from_code(code):
    local_variables = {}
    exec(code, {}, local_variables)
    return local_variables['fig']

# Parse contents of the uploaded file
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return df

# Layout with sidebar and main content
app.layout = html.Div([
    # Sidebar
    html.Div([
        html.Div([
            html.H2("Plotly AI", className="sidebar-title"),
            html.Hr(),
            html.P("Graph Builder Dashboard", className="sidebar-subtitle"),
        ], className="sidebar-header"),

        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                multiple=False
            ),
            dcc.Textarea(
                id="user-request",
                placeholder="Describe the plot you want to create...",
                className="input-textarea"
            ),
            html.Button(
                "Generate Plot",
                id="my-button",
                className="submit-button"
            ),
        ], className="sidebar-content")
    ], className="sidebar"),

    # Main Content
    html.Div([
        # Top Stats Cards
        html.Div([
            html.Div([
                html.H4("Total Records", className="card-title"),
                html.P(id="total-records", className="card-value"),
                html.P("Total rows in dataset", className="card-subtitle")
            ], className="stats-card"),
            html.Div([
                html.H4("Columns", className="card-title"),
                html.P(id="num-columns", className="card-value"),
                html.P("Available features", className="card-subtitle")
            ], className="stats-card"),
            html.Div([
                html.H4("Date Range", className="card-title"),
                html.P(id="date-range", className="card-value"),
                html.P("Time period covered", className="card-subtitle")
            ], className="stats-card"),
        ], className="stats-container"),

        # Data Grid and Graph Container
        html.Div([
            # Data Grid
            html.Div([
                html.H3("Dataset Preview", className="section-title"),
                html.Div([
                    dag.AgGrid(
                        id="data-grid",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "filter": True,
                            "sortable": True,
                            "floatingFilter": True,
                            "resizable": True
                        },
                        className="ag-theme-alpine",
                    )
                ], className="grid-container"),
            ], className="data-section"),

            # Graph Output
            html.Div([
                html.H3("Visualization", className="section-title"),
                html.Div([
                    dcc.Loading(
                        html.Div(id="my-figure", className="graph-output"),
                        type="circle",
                        color="#6366F1"
                    ),
                    dcc.Markdown(id="content", className="response-text"),
                ], className="graph-container"),
            ], className="visualization-section"),
        ], className="main-grid"),

    ], className="main-content"),

    # Hidden elements
    dcc.Store(id="store-it", data=[]),
    dcc.Store(id="uploaded-data", data=None),

], className="dashboard-container")

# Callback to handle file upload
@callback(
    [Output("data-grid", "rowData"),
     Output("data-grid", "columnDefs"),
     Output("total-records", "children"),
     Output("num-columns", "children"),
     Output("date-range", "children"),
     Output("uploaded-data", "data")],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")],
    prevent_initial_call=True,
)
def update_output(contents, filename):
    if contents is not None:
        df = parse_contents(contents, filename)
        total_records = len(df)
        num_columns = len(df.columns)
        date_range = f"{df['year'].min()} - {df['year'].max()}" if 'year' in df.columns else 'N/A'

        return (df.to_dict("records"),
                [{"field": i} for i in df.columns],
                f"{total_records:,}",
                f"{num_columns}",
                date_range,
                df.to_json(date_format='iso', orient='split'))
    return no_update

# Callback to generate the graph
@callback(
    [Output("my-figure", "children"), Output("content", "children"), Output("store-it", "data")],
    [Input("my-button", "n_clicks")],
    [State("user-request", "value"), State("store-it", "data"), State("uploaded-data", "data")],
    prevent_initial_call=True,
)
def create_graph(_, user_input, chat_history, uploaded_data):
    if len(chat_history) > 0:
        chat_history = loads(chat_history)

    if uploaded_data is not None:
        df = pd.read_json(uploaded_data, orient='split')
        df_5_rows = df.head()
        csv_string = df_5_rows.to_string(index=False)

        response = chain.invoke({"input": user_input, "data": csv_string, "chat_history": chat_history})
        result_output = response.content

        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=result_output))
        history = dumps(chat_history)

        # Check for code block
        code_block_match = re.search(r'```(?:[Pp]ython)?(.*?)```', result_output, re.DOTALL)
        if code_block_match:
            code_block = code_block_match.group(1).strip()
            cleaned_code = re.sub(r'(?m)^\s*fig\.show\(\)\s*$', '', code_block)
            fig = get_fig_from_code(cleaned_code)
            return dcc.Graph(figure=fig), result_output, history
        else:
            return no_update, result_output, history
    else:
        return no_update, "Please upload a CSV file first.", no_update

# Add custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary-color: #6366F1;
                --sidebar-width: 300px;
                --card-bg: #ffffff;
                --border-color: #e5e7eb;
            }

            body {
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                background-color: #f3f4f6;
            }

            .dashboard-container {
                display: flex;
                min-height: 100vh;
            }

            .sidebar {
                width: var(--sidebar-width);
                background-color: white;
                border-right: 1px solid var(--border-color);
                padding: 1.5rem;
                position: fixed;
                height: 100vh;
                box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
                overflow-y: auto;
            }

            .sidebar-title {
                color: var(--primary-color);
                font-size: 1.5rem;
                margin: 0;
            }

            .sidebar-subtitle {
                color: #6b7280;
                font-size: 0.875rem;
            }

            .sidebar-header {
                margin-bottom: 2rem;
            }

            .main-content {
                flex: 1;
                padding: 2rem;
                margin-left: var(--sidebar-width);
            }

            .stats-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }

            .stats-card {
                background-color: var(--card-bg);
                padding: 1.5rem;
                border-radius: 0.5rem;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            .card-title {
                margin: 0;
                color: #1f2937;
                font-size: 1rem;
                font-weight: 500;
            }

            .card-value {
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--primary-color);
                margin: 0.5rem 0;
            }

            .card-subtitle {
                color: #6b7280;
                margin: 0;
                font-size: 0.875rem;
            }

            .main-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 2rem;
            }

            .section-title {
                margin: 0 0 1rem 0;
                color: #1f2937;
                font-size: 1.25rem;
                font-weight: 500;
            }

            .data-section, .visualization-section {
                background-color: var(--card-bg);
                padding: 1.5rem;
                border-radius: 0.5rem;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            .grid-container {
                height: 400px;
                width: 100%;
            }

            .graph-container {
                min-height: 500px;
            }

            .graph-output {
                margin-bottom: 1rem;
            }

            .input-textarea {
                width: 100%;
                min-height: 120px;
                padding: 0.75rem;
                border: 1px solid var(--border-color);
                border-radius: 0.375rem;
                margin-bottom: 1rem;
                resize: vertical;
                font-size: 0.875rem;
            }

            .submit-button {
                width: 100%;
                padding: 0.75rem;
                background-color: var(--primary-color);
                color: white;
                border: none;
                border-radius: 0.375rem;
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.2s;
            }

            .submit-button:hover {
                background-color: #4f46e5;
            }

            .response-text {
                margin-top: 1rem;
                font-size: 0.875rem;
                color: #4b5563;
                padding: 1rem;
                background-color: #f9fafb;
                border-radius: 0.375rem;
                border: 1px solid var(--border-color);
            }

            /* AG Grid Theme Overrides */
            .ag-theme-alpine {
                --ag-background-color: transparent;
                --ag-header-background-color: #f9fafb;
                --ag-odd-row-background-color: #ffffff;
                --ag-row-hover-color: #f3f4f6;
                --ag-selected-row-background-color: #eff6ff;
                --ag-font-size: 0.875rem;
                height: 100%;
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .sidebar {
                    width: 100%;
                    height: auto;
                    position: relative;
                }

                .main-content {
                    margin-left: 0;
                }

                .stats-container {
                    grid-template-columns: 1fr;
                }

                .main-grid {
                    grid-template-columns: 1fr;
                }
            }

            /* Scrollbar Styling */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }

            ::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 4px;
            }

            ::-webkit-scrollbar-thumb {
                background: #c5c6c9;
                border-radius: 4px;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: #a8a9ad;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

if __name__ == "__main__":
    app.run_server(debug=True, port=8009)
