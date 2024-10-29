# Plotly AI Graph Builder

An interactive web application that combines the power of AI with Plotly's visualization capabilities to automatically generate data visualizations from natural language descriptions. Built with Dash, LangChain, and Groq LLM, powered by LLaMA.
You can test it here: [Demo Link](https://dataviz-ai-builder.onrender.com/)

## Features

- 🤖 AI-powered graph generation using natural language
- 🦙 Powered by LLaMA 3 70B model
- 📊 Interactive data visualization with Plotly
- 📈 Real-time data preview with AG Grid
- 📁 CSV and Excel file upload support
- 📊 Automatic dataset statistics
- 💬 Conversation history for context-aware interactions
- 🎨 Modern, responsive UI design

## How It Works

The application follows a simple but powerful workflow:

1. **Data Input**
   - Users upload their CSV/Excel file
   - The system automatically generates statistics and previews the data

2. **Natural Language Processing**
   - Users describe their desired visualization in plain English
   - The request is processed by LLaMA 3 70B, a powerful large language model
   - LLaMA understands the context and requirements from the natural language input

3. **Code Generation**
   - LLaMA generates appropriate Plotly code based on the request
   - The system includes data preprocessing and visualization parameters
   - The generated code is optimized for the specific dataset

4. **Visualization Rendering**
   - The generated Plotly code is executed
   - The visualization is rendered in real-time
   - Users can interact with the resulting graph

5. **Conversation Context**
   - The system maintains conversation history
   - Subsequent requests can reference previous visualizations
   - The AI understands and builds upon previous context
  
## Screen Ui
![Plotly AI Graph Builder Image](https://github.com/verus56/Plotly-AI-Graph-Builder/blob/main/1.png)
![Plotly AI Graph Builder Image2](https://github.com/verus56/Plotly-AI-Graph-Builder/blob/main/2.png)

## About LLaMA

This application uses LLaMA 3 70B, accessed through Groq's API. LLaMA (Large Language Model Meta AI) is a powerful language model known for:

- High-quality code generation
- Strong understanding of data visualization concepts
- Efficient processing of technical requirements
- Ability to understand context and nuanced requests
- Advanced pattern recognition in data structures

[Rest of README remains the same from Prerequisites section onwards...]

## Prerequisites

Before running the application, make sure you have:

- Python 3.7+
- Groq API key
- Required Python packages (listed in requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd plotly-ai-graph-builder
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Set up your Groq API key:
   - Replace `GROQ_API_KEY` in the code with your actual API key
   - Or set it as an environment variable:
```bash
export GROQ_API_KEY='your-api-key-here'
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8009
```

3. Use the application:
   - Upload your CSV or Excel file using the upload button
   - Enter your visualization request in natural language
   - Click "Generate Plot" to create the visualization

## Application Structure

The dashboard consists of several key components:

- **Sidebar**
  - File upload interface
  - Text input for visualization requests
  - Generate plot button

- **Main Content**
  - Statistics cards showing dataset information
  - Interactive data grid for dataset preview
  - Visualization output area
  - AI response display

## Key Dependencies

- `dash`: Web application framework
- `langchain`: LLM interaction framework
- `langchain_groq`: Groq LLM integration
- `plotly`: Data visualization library
- `dash-ag-grid`: Interactive data grid component
- `pandas`: Data manipulation and analysis

## Customization

### Changing the LLM Model

You can switch between different Groq models by modifying the model parameter:

```python
model = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama3-70b-8192",  # Current model
    # model="Mixtral-8x7b-32768"  # Alternative model
)
```

### Styling

The application uses custom CSS for styling, which can be modified in the `app.index_string` section. The main style variables are:

```css
:root {
    --primary-color: #6366F1;
    --sidebar-width: 300px;
    --card-bg: #ffffff;
    --border-color: #e5e7eb;
}
```

## Error Handling

The application includes error handling for:
- File upload errors
- Invalid data formats
- AI response processing
- Code execution errors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Dash](https://dash.plotly.com/)
- Powered by [Groq](https://groq.com/)
- Visualization by [Plotly](https://plotly.com/)
- Data grid by [AG Grid](https://www.ag-grid.com/)
- LLaMA by [Meta AI](https://ai.meta.com/)
