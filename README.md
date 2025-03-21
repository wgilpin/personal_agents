# Plan and Execute Agent

A powerful AI-driven workflow system that implements the "Plan and Execute" approach to problem-solving with Large Language Models (LLMs).

## Project Overview

This project combines a Python FastAPI backend with a Vue.js frontend to create a system for building, visualizing, and executing AI workflows. The implementation is based on the "Plan-and-Solve Prompting" methodology described in academic research, enhanced with additional features like goal assessment and dynamic replanning.

### Key Features

- **Plan and Execute Workflow**: Break down complex problems into manageable steps
- **Visual Flowchart Builder**: Create and modify workflows through an intuitive UI
- **API-Driven Architecture**: Separate backend and frontend for flexibility
- **Goal Assessment**: Evaluate if the original goal has been satisfied
- **Dynamic Replanning**: Modify plans based on execution results
- **Workflow Logging**: Automatically record execution details for all workflows

## System Requirements

- Python 3.8+
- Node.js and npm
- OpenAI API key
- Tavily API key (for search functionality)

## Installation

1. Clone this repository
2. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   TAVILY_API_KEY=your_tavily_key
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Vue.js dependencies:
   ```bash
   cd src/ui/vue-app
   npm install
   ```

## Starting the Servers

### API Server

The backend API server is built with FastAPI and provides endpoints for executing workflows, managing flowcharts, and more.

To start the API server:

```bash
python src/api_server.py
```

This will launch the server at `http://localhost:8000` with automatic reload enabled.

### UI Server

The frontend is built with Vue.js and provides a visual interface for creating and managing workflows.

To start the UI server:

```bash
cd src/ui/vue-app
npm run serve
```

This will launch the development server at `http://localhost:8080` with hot-reload enabled.

## Project Structure

- `src/api_server.py`: FastAPI server implementation
- `src/plan_and_execute.py`: Core implementation of the Plan and Execute agent
- `src/workflows.py`: Workflow management utilities
- `src/workflow_logger.py`: Logging functionality for workflow executions
- `src/view_workflow_logs.py`: Utility to view and filter workflow logs
- `src/ui/vue-app/`: Vue.js frontend application
  - `src/components/`: Vue components including FlowchartCanvas, FlowchartNode, etc.
- `src/workflows/`: YAML workflow definitions
- `src/flowcharts/`: Flowchart configurations
- `logs/`: Directory where workflow execution logs are stored

## API Endpoints

The API server provides several endpoints:

- `/execute`: Execute a prompt using the plan_and_execute workflow
- `/flowchart`: Upload a YAML flowchart file
- `/flowchart/current/execute`: Execute the current flowchart
- `/workflows`: List all available workflows
- `/workflows/{filename}`: Get a specific workflow
- `/workflows/{filename}/execute`: Execute a specific workflow

## Workflow Logging

The system now includes automatic logging of all workflow executions. Each time a workflow completes (successfully or with errors), a log file is created with detailed information about the execution.

### Log Information

Each log entry includes:
- Workflow name
- Start date and time
- End date and time
- Execution duration in seconds
- Success status
- Final result value
- Error message (if applicable)

### Viewing Logs

A utility script is provided to view and filter workflow execution logs:

```bash
python src/view_workflow_logs.py --list         # List all logs
python src/view_workflow_logs.py --latest       # View the most recent log
python src/view_workflow_logs.py --workflow "My Workflow"  # Filter by workflow name
python src/view_workflow_logs.py --start-date 2025-03-01   # Filter by date
python src/view_workflow_logs.py --verbose      # Show full result details
```

Run `python src/view_workflow_logs.py --help` for a complete list of options.

## Frontend Components

The Vue.js application is organized into the following components:

- **App.vue**: The main application component
- **Toolbar.vue**: Handles the toolbar UI with buttons for creating nodes and managing the flowchart
- **FlowchartCanvas.vue**: Manages the canvas where nodes and connections are rendered
- **FlowchartNode.vue**: Represents an individual node in the flowchart
- **WorkflowStatusModal.vue**: Displays workflow execution status and results

## Development

For development purposes, the Vue.js application proxies API requests to the backend server to avoid CORS issues. Make sure both servers are running during development.

### Running Tests

The project includes comprehensive test coverage for both backend and frontend components.

#### Backend Tests

To run the backend tests:

```bash
python src/run_tests.py
```

#### Test Coverage

To generate backend test coverage reports:

```bash
python src/run_coverage.py
```

This will:
- Run all backend tests with coverage analysis
- Generate a terminal report showing coverage percentages
- Create an HTML report in the `htmlcov` directory
- Create an XML report at `coverage.xml`

The coverage report shows which parts of your code are covered by tests and helps identify areas that need additional testing.

Current coverage metrics:
- api_server.py: 65%
- plan_and_execute.py: 47%
- view_workflow_logs.py: 8%
- workflow_logger.py: 100%
- Overall: 45%

#### Frontend Tests

To run the frontend tests:

```bash
cd src/ui/vue-app
npm run test:unit
```

To run frontend tests with coverage:

```bash
cd src/ui/vue-app
npm run test:coverage
```

#### Combined Coverage Reports

To run both backend and frontend tests with coverage and open the reports:

```bash
python src/run_all_coverage.py
```

This script will:
1. Run backend tests with coverage
2. Run frontend tests with coverage
3. Open both HTML coverage reports in your default browser

## References

- [Plan-and-Solve Prompting Paper](https://arxiv.org/pdf/2305.04091)
- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [LangChain Documentation](https://github.com/langchain-ai/langchain)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue.js Documentation](https://vuejs.org/)