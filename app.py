from dash import Dash, html, dcc, callback, Output, Input, State, no_update
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain.load import dumps, loads

import dash_ag_grid as dag
import pandas as pd
import base64
import io
import os
import re

# Groq API Key
GROQ_API_KEY = ''

# Choose the model
model = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama3-70b-8192",
)

prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You're a data visualization expert and only use Plotly. "
     "Here are the first 5 rows of the uploaded data: {data} Follow the user's instructions when creating the graph."),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
])

chain = prompt | model

# Extract Plotly fig object from the generated code
def get_fig_from_code(code):
    try:
        local_variables = {}
        exec(code, globals(), local_variables)
        return local_variables.get('fig', None)
    except Exception as e:
        print(f"Error executing code: {str(e)}")
        return None

# Parse uploaded file content
def parse_contents(contents):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        return df
    except Exception as e:
        print(f"Error parsing file: {str(e)}")
        return None

# Initialize the Dash app
app = Dash(__name__)
server = app.server  # This is the underlying Flask app
app.title = "Plotly AI Graph Builder "

# Layout with sidebar and main content
app.layout = html.Div([
    # Sidebar
    html.Div([
        html.Div([
            html.H2("Plotly AI Graph Builder", className="sidebar-title"),
            html.Hr(),
            html.P("Graph Builder Dashboard", className="sidebar-subtitle"),
        ], className="sidebar-header"),
        
        html.Div([
            # Add file upload component
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select CSV File')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px 0'
                },
                multiple=False
            ),
            html.Div(id='upload-status', style={'margin': '10px 0', 'color': '#666'}),
            dcc.Textarea(
                id="user-request",
                placeholder="Describe the plot you want to create...",
                className="input-textarea"
            ),
            html.Button(
                "Generate Plot",
                id="my-button",
                className="submit-button",
                disabled=True
            ),
        ], className="sidebar-content")
    ], className="sidebar"),
    
    # Main Content
    html.Div([
        # Top Stats Cards
        html.Div(id='stats-container', className="stats-container"),
        
        # Data Grid and Graph Container
        html.Div([
            # Data Grid
            html.Div([
                html.H3("Dataset Preview", className="section-title"),
                html.Div(id='data-grid', className="grid-container"),
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
    dcc.Store(id="dataset-store", data=None),
], className="dashboard-container")

# Callback to handle file upload
@callback(
    [Output('dataset-store', 'data'),
     Output('upload-status', 'children'),
     Output('my-button', 'disabled'),
     Output('stats-container', 'children'),
     Output('data-grid', 'children')],
    Input('upload-data', 'contents'),
    prevent_initial_call=True
)
def update_output(contents):
    if contents is None:
        return no_update, no_update, True, no_update, no_update
    
    df = parse_contents(contents)
    if df is None:
        return (None, 
                "Error processing file. Please ensure it's a valid CSV.",
                True,
                no_update,
                no_update)
    
    # Create stats cards
    total_records = len(df)
    num_columns = len(df.columns)
    date_range = f"{df['year'].min()} - {df['year'].max()}" if 'year' in df.columns else 'N/A'
    
    stats_cards = [
        html.Div([
            html.H4("Total Records", className="card-title"),
            html.P(f"{total_records:,}", className="card-value"),
            html.P("Total rows in dataset", className="card-subtitle")
        ], className="stats-card"),
        html.Div([
            html.H4("Columns", className="card-title"),
            html.P(f"{num_columns}", className="card-value"),
            html.P("Available features", className="card-subtitle")
        ], className="stats-card"),
        html.Div([
            html.H4("Date Range", className="card-title"),
            html.P(date_range, className="card-value"),
            html.P("Time period covered", className="card-subtitle")
        ], className="stats-card"),
    ]
    
    # Create data grid
    data_grid = dag.AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=[{"field": i} for i in df.columns],
        defaultColDef={
            "filter": True,
            "sortable": True,
            "floatingFilter": True,
            "resizable": True
        },
        className="ag-theme-alpine",
    )
    
    return (df.to_json(date_format='iso', orient='split'),
            f"File uploaded successfully: {total_records:,} rows",
            False,
            stats_cards,
            data_grid)

# Callback for graph generation
@callback(
    [Output("my-figure", "children"),
     Output("content", "children"),
     Output("store-it", "data")],
    [Input("my-button", "n_clicks")],
    [State("user-request", "value"),
     State("store-it", "data"),
     State("dataset-store", "data")],
    prevent_initial_call=True
)
def create_graph(n_clicks, user_input, chat_history, dataset_json):
    if n_clicks is None or not user_input or dataset_json is None:
        return no_update, "Please upload a dataset and enter a visualization request.", []
    
    try:
        df = pd.read_json(dataset_json, orient='split')
        csv_string = df.head().to_string(index=False)
        
        # Initialize chat history if empty
        if not chat_history:
            chat_history = []
        elif isinstance(chat_history, str):
            try:
                chat_history = loads(chat_history)
            except:
                chat_history = []
        
        # Generate the response
        response = chain.invoke({
            "input": user_input,
            "data": csv_string,
            "chat_history": chat_history
        })
        result_output = response.content

        # Update chat history
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=result_output))
        history = dumps(chat_history)

        # Extract and execute code
        code_block_match = re.search(r'```(?:[Pp]ython)?(.*?)```', result_output, re.DOTALL)
        if code_block_match:
            code_block = code_block_match.group(1).strip()
            cleaned_code = re.sub(r'(?m)^\s*fig\.show\(\)\s*$', '', code_block)
            
            # Make DataFrame available to the code
            globals()['df'] = df
            fig = get_fig_from_code(cleaned_code)
            
            if fig is not None:
                return dcc.Graph(figure=fig), result_output, history
            else:
                return no_update, "Error generating the visualization. Please try a different request.", history
        else:
            return no_update, result_output, history
            
    except Exception as e:
        print(f"Error in create_graph: {str(e)}")
        return no_update, f"An error occurred: {str(e)}", []

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
