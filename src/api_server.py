#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API server for plan_and_execute.py"""

import json
import os
import datetime
from typing import Any, Dict, List, Optional

import uvicorn  # pylint: disable=import-error
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile  # pylint: disable=import-error
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from plan_and_execute import PlanAndExecuteAgent
from workflows import (
    save_workflow,
    list_workflows as get_workflows,
    delete_workflow,
    update_workflow_name as update_workflow_name_func,
    load_workflow,
)
from workflow_logger import log_workflow_execution
from view_workflow_logs import list_log_files, parse_log_file, filter_logs

# Load environment variables
load_dotenv()


# Create FastAPI app
api = FastAPI(title="Workflow API", description="API for workflow execution")

print("Server starting...")

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


class WorkflowResponse(BaseModel):
    """Response model for the workflow endpoint."""

    success: bool
    message: str


@api.post("/workflows", response_model=WorkflowResponse)
async def upload_workflow(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a workflow to be used by the AI server.

    Args:
        file: The JSON file containing the workflow data.

    Returns:
        A dictionary indicating success or failure.
    """
    try:
        # Check if the file is a JSON file
        if not file.filename.endswith(".json"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "File must be a JSON file"},
            )

        # Read the file content
        content = await file.read()

        # Use the workflow module to save the file
        success, message, _ = save_workflow(content)

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


@api.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows() -> List[Dict[str, Any]]:
    """
    List all available workflows from the workflows directory.

    Returns:
        A list of workflow information including name, filename, and description.
    """
    try:
        # Use the function from workflows.py to get the list of workflows
        workflows = await get_workflows()
        return workflows
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
        # Extract workflow ID from filename
        workflow_id = filename

        # Load the workflow from the database
        workflow_data = await load_workflow(workflow_id)

        if not workflow_data:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred while reading workflow: {str(e)}") from e

    return workflow_data


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
    # Record start time
    start_time = datetime.datetime.now()

    # Extract workflow ID from filename
    workflow_id = filename

    # Load the workflow from the database
    workflow_data = await load_workflow(workflow_id)
    if not workflow_data:
        raise HTTPException(
            status_code=404, detail=f"An error occurred while reading workflow: Workflow '{workflow_id}' not found"
        )

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
        # Use the workflow module to update the name
        result = update_workflow_name_func(filename, request.name)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        # Return success
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
    # Load the workflow from the database
    workflow_id = filename
    workflow_data = await load_workflow(workflow_id)

    if not workflow_data:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    try:
        workflow_name = workflow_data.get("metadata", {}).get("name", workflow_id)

        logs_dir = os.path.join(os.path.dirname(__file__), "logs")

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
