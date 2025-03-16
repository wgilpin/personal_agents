#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API server for plan_and_execute.py"""

import json
import os
import datetime
from typing import Any, Dict, List, Optional

import uvicorn  # pylint: disable=import-error
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile  # pylint: disable=import-error
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from plan_and_execute import PlanAndExecuteAgent
from workflows import (
    save_workflow_from_yaml,
    list_workflows as get_workflows,
    delete_workflow,
    update_workflow_name as update_workflow,
)
from workflow_logger import log_workflow_execution
from view_workflow_logs import list_log_files, parse_log_file, filter_logs

# Load environment variables
load_dotenv()


# Create FastAPI app
api = FastAPI(title="Plan and Execute API", description="API for plan_and_execute.py")

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


class PromptInput(BaseModel):
    """Input model for the execute endpoint."""

    input: str


class ApiResponse(BaseModel):
    """Response model for the execute endpoint."""

    result: str = Field(description="The result of the execution")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class WorkflowExecuteRequest(BaseModel):
    """Request model for the workflow execution endpoint."""

    input: str = Field(description="The input text to process with the workflow")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional configuration for the workflow execution"
    )


class WorkflowExecuteResponse(BaseModel):
    """Response model for the workflow execution endpoint."""

    final_result: str = Field(description="The final result of the workflow execution")
    goal_assessment_result: Optional[str] = Field(
        default=None, description="The goal assessment result as a JSON string"
    )
    goal_assessment_feedback: Optional[str] = Field(default=None, description="Feedback from the goal assessment")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


@api.post("/execute", response_model=ApiResponse)
async def execute_prompt(prompt_input: PromptInput) -> Dict[str, Any]:
    """
    Execute a prompt using the plan_and_execute workflow.

    Args:
        prompt_input: The input prompt.

    Returns:
        A dictionary containing the execution result.
    """
    try:
        # Create a plan_and_execute agent
        agent = PlanAndExecuteAgent()

        # Execute the agent with the input
        result = await agent.run(prompt_input.input)

        # Extract the final result
        final_result = result.get("final_result", "No result")

        return {"result": final_result}
    except Exception as e:
        # Handle all other exceptions
        error_message = f"An error occurred: {str(e)}"
        print(f"\n\n{error_message}")
        return {"result": "", "error": error_message}


class FlowchartResponse(BaseModel):
    """Response model for the flowchart endpoint."""

    success: bool
    message: str


@api.post("/flowchart", response_model=FlowchartResponse)
async def upload_flowchart(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a YAML flowchart file to be used by the AI server.

    Args:
        file: The YAML file containing the flowchart data.

    Returns:
        A dictionary indicating success or failure.
    """
    try:
        # Check if the file is a YAML file
        if not file.filename.endswith((".yaml", ".yml")):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "File must be a YAML file"},
            )

        # Read the file content
        content = await file.read()

        # Use the workflow module to save the file
        success, message, _ = save_workflow_from_yaml(content)

        if not success:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": message},
            )

        return {
            "success": True,
            "message": message,
        }

    except Exception as e:
        # Handle exceptions
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"An error occurred: {str(e)}"},
        )


@api.post("/flowchart/current/execute", response_model=WorkflowExecuteResponse)
async def execute_current_flowchart(request: WorkflowExecuteRequest) -> Dict[str, Any]:
    """
    Execute the current flowchart.

    Args:
        request: The execution request containing input and optional configuration.

    Returns:
        The results of the flowchart execution.
    """
    # Get the flowchart file path
    flowchart_path = os.path.join(os.path.dirname(__file__), "flowcharts", "current_flowchart.yaml")

    # Check if the file exists
    if not os.path.exists(flowchart_path):
        raise HTTPException(status_code=404, detail="Current flowchart not found")

    # Record start time
    start_time = datetime.datetime.now()

    # Load the flowchart file
    with open(flowchart_path, "r", encoding="utf-8") as f:
        flowchart_data = yaml.safe_load(f)

    # Create an agent
    agent = PlanAndExecuteAgent()

    # Execute the flowchart by traversing the nodes
    try:
        # Build a node map for quick lookup
        node_map = {}
        if "nodes" in flowchart_data and flowchart_data["nodes"]:
            for node in flowchart_data["nodes"]:
                if "id" in node:
                    node_map[node["id"]] = node

        # Build a connection map to find next nodes
        connection_map = {}
        if "connections" in flowchart_data and flowchart_data["connections"]:
            for connection in flowchart_data["connections"]:
                from_node_id = connection["from"]["nodeId"]
                if from_node_id not in connection_map:
                    connection_map[from_node_id] = []
                connection_map[from_node_id].append(connection["to"]["nodeId"])

        # Find the first node (one that has no incoming connections)
        first_node_id = None
        all_destination_nodes = set()
        for connection in flowchart_data.get("connections", []):
            all_destination_nodes.add(connection["to"]["nodeId"])

        for node in flowchart_data.get("nodes", []):
            if node["id"] not in all_destination_nodes:
                first_node_id = node["id"]
                break

        # If no starting node found, use the first node in the list
        if first_node_id is None and flowchart_data.get("nodes"):
            first_node_id = flowchart_data["nodes"][0]["id"]

        # Execute each node in sequence, following the connections
        current_node_id = first_node_id
        final_result = ""
        current_state = request.input  # Initial state from request

        while current_node_id and current_node_id in node_map:
            current_node = node_map[current_node_id]

            # Get the prompt from the current node
            node_prompt = current_node.get("prompt", "")

            # Execute the node with the current state as context
            prompt_with_context = f"{node_prompt}\nContext from previous steps: {current_state}"
            result = await agent.run(prompt_with_context, request.config)

            # Update the current state with the result
            current_state = result.get("final_result", "")

            # Find the next node to execute
            next_nodes = connection_map.get(current_node_id, [])
            current_node_id = next_nodes[0] if next_nodes else None

        # Use the final state as the result
        result = {"final_result": current_state}

        # Extract all relevant fields from the result
        final_result = result.get("final_result", "")
        goal_assessment_result = result.get("goal_assessment_result")
        goal_assessment_feedback = result.get("goal_assessment_feedback")
        error = result.get("error")

        # Check if final_result is already JSON-formatted
        try:
            # Try to parse it as JSON to see if it's valid
            json.loads(final_result)
            # If it's valid JSON, return it as is
            json_formatted = final_result
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, wrap it in a JSON structure
            json_formatted = json.dumps({"response_text": final_result})

        # Record end time
        end_time = datetime.datetime.now()

        # Get workflow name from metadata
        workflow_name = flowchart_data.get("metadata", {}).get("name", "Current Flowchart")

        # Log the workflow execution
        log_workflow_execution(
            workflow_name=workflow_name, start_time=start_time, end_time=end_time, result=json_formatted
        )

        return {
            "final_result": json_formatted,
            "goal_assessment_result": goal_assessment_result,
            "goal_assessment_feedback": goal_assessment_feedback,
            "error": error,
        }
    except Exception as e:
        # Handle exceptions
        error_message = f"An error occurred while executing flowchart: {str(e)}"

        # Record end time for error case
        end_time = datetime.datetime.now()

        # Log the failed execution
        log_workflow_execution(
            workflow_name=(
                flowchart_data.get("metadata", {}).get("name", "Current Flowchart")
                if "flowchart_data" in locals()
                else "Current Flowchart"
            ),
            start_time=start_time if "start_time" in locals() else datetime.datetime.now(),
            end_time=end_time,
            result=None,
            success=False,
            error=error_message,
        )
        print(f"\n\n{error_message}")
        raise HTTPException(status_code=500, detail=error_message) from e


@api.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows() -> List[Dict[str, Any]]:
    """
    List all available workflows from the workflows directory.

    Returns:
        A list of workflow information including name, filename, and description.
    """
    try:
        # Use the function from workflows.py to get the list of workflows
        return await get_workflows()
    except Exception as e:
        # Handle exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred while listing workflows: {str(e)}") from e


@api.get("/workflows/{filename}", response_model=Dict[str, Any])
async def get_workflow(filename: str) -> Dict[str, Any]:
    """
    Get a specific workflow by filename.

    Args:
        filename: The name of the workflow file.

    Returns:
        The workflow data.
    """
    try:
        # Get the workflow file path
        workflow_path = os.path.join(os.path.dirname(__file__), "workflows", filename)

        # Check if the file exists
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")

        # Read and parse the workflow file
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        return workflow_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred while reading workflow: {str(e)}") from e


@api.post("/workflows/{filename}/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(filename: str, request: WorkflowExecuteRequest) -> Dict[str, Any]:
    """
    Execute a specific workflow by filename.

    Args:
        filename: The name of the workflow file.
        request: The execution request containing input and optional configuration.

    Returns:
        The results of the workflow execution.
    """
    # Get the workflow file path
    workflow_path = os.path.join(os.path.dirname(__file__), "workflows", filename)

    # Check if the file exists
    if not os.path.exists(workflow_path):
        raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")

    # Record start time
    start_time = datetime.datetime.now()

    # Load the workflow file
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = yaml.safe_load(f)

    # Create an agent
    agent = PlanAndExecuteAgent()

    # Execute the workflow by traversing the nodes
    try:
        # Build a node map for quick lookup
        node_map = {}
        if "nodes" in workflow_data and workflow_data["nodes"]:
            for node in workflow_data["nodes"]:
                if "id" in node:
                    node_map[node["id"]] = node

        # Build a connection map to find next nodes
        connection_map = {}
        if "connections" in workflow_data and workflow_data["connections"]:
            for connection in workflow_data["connections"]:
                from_node_id = connection["from"]["nodeId"]
                if from_node_id not in connection_map:
                    connection_map[from_node_id] = []
                connection_map[from_node_id].append(connection["to"]["nodeId"])

        # Find the first node (one that has no incoming connections)
        first_node_id = None
        all_destination_nodes = set()
        for connection in workflow_data.get("connections", []):
            all_destination_nodes.add(connection["to"]["nodeId"])

        for node in workflow_data.get("nodes", []):
            if node["id"] not in all_destination_nodes:
                first_node_id = node["id"]
                break

        # If no starting node found, use the first node in the list
        if first_node_id is None and workflow_data.get("nodes"):
            first_node_id = workflow_data["nodes"][0]["id"]

        # Execute each node in sequence, following the connections
        current_node_id = first_node_id
        final_result = ""
        current_state = request.input  # Initial state from request

        while current_node_id and current_node_id in node_map:
            current_node = node_map[current_node_id]

            # Get the prompt from the current node
            node_prompt = current_node.get("prompt", "")

            # Execute the node with the current state as context
            prompt_with_context = f"{node_prompt}\nContext from previous steps: {current_state}"
            result = await agent.run(prompt_with_context, request.config)

            # Update the current state with the result
            current_state = result.get("goal_assessment_result", "")

            # Find the next node to execute
            next_nodes = connection_map.get(current_node_id, [])
            current_node_id = next_nodes[0] if next_nodes else None

        # Use the final state as the result
        result = {"final_result": current_state}

        # Extract all relevant fields from the result
        final_result = result.get("final_result", "")
        goal_assessment_result = result.get("goal_assessment_result")
        goal_assessment_feedback = result.get("goal_assessment_feedback")
        error = result.get("error")

        # Check if final_result is already JSON-formatted
        try:
            # Try to parse it as JSON to see if it's valid
            json.loads(final_result)
            # If it's valid JSON, return it as is
            json_formatted = final_result
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, wrap it in a JSON structure
            json_formatted = json.dumps({"response_text": final_result})

        # Debug print
        print(f"Result from agent: {result}")
        print(f"Returning: final_result={json_formatted}, goal_assessment_result={goal_assessment_result}")

        response_data = {
            "final_result": json_formatted,
            "goal_assessment_result": goal_assessment_result,
            "goal_assessment_feedback": goal_assessment_feedback,
            "error": error,
        }

        # Debug print
        print(f"Response data: {response_data}")

        # Record end time
        end_time = datetime.datetime.now()

        # Get workflow name from metadata
        workflow_name = workflow_data.get("metadata", {}).get("name", filename)

        # Log the workflow execution
        log_workflow_execution(
            workflow_name=workflow_name, start_time=start_time, end_time=end_time, result=json_formatted
        )

        return response_data
    except Exception as e:
        # Handle exceptions
        error_message = f"An error occurred while executing workflow: {str(e)}"

        # Record end time for error case
        end_time = datetime.datetime.now()

        # Log the failed execution
        log_workflow_execution(
            workflow_name=(
                workflow_data.get("metadata", {}).get("name", filename) if "workflow_data" in locals() else filename
            ),
            start_time=start_time if "start_time" in locals() else datetime.datetime.now(),
            end_time=end_time,
            result=None,
            success=False,
            error=error_message,
        )
        print(f"\n\n{error_message}")
        raise HTTPException(status_code=500, detail=error_message) from e


@api.delete("/workflows/{filename}", response_model=Dict[str, Any])
async def delete_workflow_endpoint(filename: str) -> Dict[str, Any]:
    """
    Delete a specific workflow by filename.

    Args:
        filename: The name of the workflow file to delete.

    Returns:
        A dictionary indicating success or failure.
    """
    try:
        # Prevent deletion of current_flowchart.yaml
        if filename == "current_flowchart.yaml":
            raise HTTPException(status_code=400, detail="Cannot delete the current flowchart")

        # Use the workflow module to delete the workflow
        result = delete_workflow(filename)

        if not result["success"]:
            raise HTTPException(status_code=404 if "not found" in result["message"] else 500, detail=result["message"])

        return {"success": True, "message": result["message"]}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
        error_message = f"An error occurred while deleting workflow: {str(e)}"
        print(f"\n\n{error_message}")
        raise HTTPException(status_code=500, detail=error_message) from e


class UpdateWorkflowNameRequest(BaseModel):
    """Request model for updating a workflow name."""

    name: str = Field(description="The new name for the workflow")


@api.put("/workflows/{filename}/name", response_model=Dict[str, Any])
async def update_workflow_name(filename: str, request: UpdateWorkflowNameRequest) -> Dict[str, Any]:
    """
    Update the name of a specific workflow.

    Args:
        filename: The name of the workflow file.
        request: The request containing the new name.

    Returns:
        A dictionary indicating success or failure.
    """
    try:
        # Get the workflow file path
        workflow_path = os.path.join(os.path.dirname(__file__), "workflows", filename)

        # Check if the file exists
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")

        # Use the workflow module to update the name
        result = update_workflow(workflow_path, request.name)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return {"success": True, "message": "Workflow name updated successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
        error_message = f"An error occurred while updating workflow name: {str(e)}"
        print(f"\n\n{error_message}")
        raise HTTPException(status_code=500, detail=error_message) from e


@api.get("/workflows/{filename}/logs/latest", response_model=Dict[str, Any])
async def get_latest_workflow_log(filename: str) -> Dict[str, Any]:
    """
    Get the latest execution log for a specific workflow.

    Args:
        filename: The name of the workflow file.

    Returns:
        The latest log data for the workflow.
    """
    try:
        # Get the workflow file path to extract the workflow name
        workflow_path = os.path.join(os.path.dirname(__file__), "workflows", filename)

        # Check if the file exists
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")

        # Read the workflow file to get its name
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        workflow_name = workflow_data.get("metadata", {}).get("name", os.path.splitext(filename)[0])

        # Get the logs directory
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

        # Get all log files
        all_log_files = list_log_files(logs_dir)

        # Filter logs for this workflow
        workflow_logs = filter_logs(all_log_files, workflow_name=workflow_name)

        if not workflow_logs:
            return {"found": False, "message": "No execution logs found for this workflow"}

        # Get the latest log (first in the list since they're sorted newest first)
        latest_log = parse_log_file(workflow_logs[0])
        return {"found": True, "log": latest_log}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred while retrieving workflow logs: {str(e)}"
        ) from e


# Run the server when this file is executed directly
if __name__ == "__main__":
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)
