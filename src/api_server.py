#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API server for plan_and_execute.py"""

import json
import os
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
    extract_workflow_metadata,
    save_workflow_from_yaml,
    list_workflows as get_workflows,
    update_workflow_name as update_workflow,
)

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


@api.get("/flowchart/current", response_model=Dict[str, Any])
async def get_current_flowchart() -> Dict[str, Any]:
    """
    Get the current flowchart from the workflows directory.

    Returns:
        The current flowchart data.
    """
    try:
        # Get the flowchart file path
        flowchart_path = os.path.join(os.path.dirname(__file__), "workflows", "current_flowchart.yaml")

        # Check if the file exists
        if not os.path.exists(flowchart_path):
            raise HTTPException(status_code=404, detail="Current flowchart not found")

        # Read and parse the flowchart file
        with open(flowchart_path, "r", encoding="utf-8") as f:
            flowchart_data = yaml.safe_load(f)

        return flowchart_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred while reading flowchart: {str(e)}") from e


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
    flowchart_path = os.path.join(os.path.dirname(__file__), "workflows", "current_flowchart.yaml")

    # Check if the file exists
    if not os.path.exists(flowchart_path):
        raise HTTPException(status_code=404, detail="Current flowchart not found")

    # Load the flowchart file
    with open(flowchart_path, "r", encoding="utf-8") as f:
        flowchart_data = yaml.safe_load(f)

    # Create an agent
    agent = PlanAndExecuteAgent()

    # Find the first node in the flowchart to get its prompt
    first_node_prompt = None
    if "nodes" in flowchart_data and flowchart_data["nodes"]:
        for node in flowchart_data["nodes"]:
            if "prompt" in node and node["prompt"] is not None:
                first_node_prompt = node["prompt"]
                break

    # If no prompt found in any node, use the request input as fallback
    prompt_to_use = first_node_prompt if first_node_prompt else request.input

    # Execute the agent with the prompt from the first node
    try:
        result = await agent.run(prompt_to_use, request.config)

        # Extract all relevant fields from the result
        final_result = result.get("final_result", "")
        goal_assessment_result = result.get("goal_assessment_result")
        goal_assessment_feedback = result.get("goal_assessment_feedback")
        error = result.get("error")

        return {
            "final_result": final_result,
            "goal_assessment_result": goal_assessment_result,
            "goal_assessment_feedback": goal_assessment_feedback,
            "error": error,
        }
    except Exception as e:
        # Handle exceptions
        error_message = f"An error occurred while executing flowchart: {str(e)}"
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

    # Load the workflow file
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = yaml.safe_load(f)

    # Create an agent
    agent = PlanAndExecuteAgent()

    # Execute the agent with the input
    try:
        result = await agent.run(request.input, request.config)

        # Extract all relevant fields from the result
        final_result = result.get("final_result", "")
        goal_assessment_result = result.get("goal_assessment_result")
        goal_assessment_feedback = result.get("goal_assessment_feedback")
        error = result.get("error")

        # Debug print
        print(f"Result from agent: {result}")
        print(f"Returning: final_result={final_result}, goal_assessment_result={goal_assessment_result}")

        response_data = {
            "final_result": final_result,
            "goal_assessment_result": goal_assessment_result,
            "goal_assessment_feedback": goal_assessment_feedback,
            "error": error,
        }

        # Debug print
        print(f"Response data: {response_data}")

        return response_data
    except Exception as e:
        # Handle exceptions
        error_message = f"An error occurred while executing workflow: {str(e)}"
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


# Run the server when this file is executed directly
if __name__ == "__main__":
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)
