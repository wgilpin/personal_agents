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

# Load environment variables
load_dotenv()


def extract_workflow_metadata(file_path: str) -> dict:
    """
    Extract metadata from a workflow file.

    Args:
        file_path: Path to the workflow file

    Returns:
        A dictionary containing metadata (name, description)
    """
    metadata = {"name": "", "description": ""}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Check if metadata section exists
        if content and "metadata" in content and isinstance(content["metadata"], dict):
            if "name" in content["metadata"]:
                metadata["name"] = content["metadata"]["name"]
            if "description" in content["metadata"]:
                metadata["description"] = content["metadata"]["description"]

        # If no description in metadata, get the first node with content as a description
        if not metadata["description"] and content and "nodes" in content and content["nodes"]:
            for node in content["nodes"]:
                if node.get("content"):
                    metadata["description"] = node["content"]
                    break
    except Exception:
        pass

    return metadata


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

    goal_assessment_result: Any


class WorkflowExecuteRequest(BaseModel):
    """Request model for the workflow execution endpoint."""

    input: str = Field(description="The input text to process with the workflow")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional configuration for the workflow execution"
    )


class WorkflowExecuteResponse(BaseModel):
    """Response model for the workflow execution endpoint."""

    final_result: str = Field(description="The final result of the workflow execution")
    goal_assessment_result: Optional[str] = Field(default=None, description="The goal assessment result if available")
    goal_assessment_feedback: Optional[str] = Field(
        default=None, description="Feedback on the goal assessment if available"
    )
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


@api.post("/execute", response_model=ApiResponse)
async def execute_prompt(prompt_input: PromptInput) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Execute a prompt using the plan_and_execute workflow.

    Args:
        prompt_input: The input prompt.

    Returns:
        A dictionary containing the goal_assessment_result.
    """
    try:
        # For now, return a placeholder response
        goal_assessment_result = json.dumps({"message": "Execution endpoint is currently disabled"})
        return {"goal_assessment_result": json.loads(goal_assessment_result)}
    except Exception as e:
        # Handle all other exceptions
        error_message = f"An error occurred: {str(e)}"
        print(f"\n\n{error_message}")
        raise HTTPException(status_code=500, detail=error_message) from e


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

        # Parse the YAML content to validate it
        try:
            _ = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Invalid YAML format: {str(e)}"},
            )

        # Save the file to a specific location
        flowchart_dir = os.path.join(os.path.dirname(__file__), "flowcharts")
        os.makedirs(flowchart_dir, exist_ok=True)

        flowchart_path = os.path.join(flowchart_dir, "current_flowchart.yaml")

        with open(flowchart_path, "wb") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Flowchart saved successfully at {flowchart_path}",
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
        # Get the workflows directory path
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")

        # Check if the directory exists
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir, exist_ok=True)
            return []

        # List all YAML files in the directory
        workflows = []
        for filename in os.listdir(workflows_dir):
            if filename.endswith((".yaml", ".yml")):
                file_path = os.path.join(workflows_dir, filename)

                # Get basic file info
                default_name = os.path.splitext(filename)[0]

                # Try to extract metadata from the file
                metadata = extract_workflow_metadata(file_path)

                # Use custom name if available, otherwise use filename
                display_name = metadata["name"] if metadata["name"] else default_name
                description = metadata["description"]

                workflows.append(
                    {
                        "name": display_name,
                        "filename": filename,
                        "description": description,
                        "default_name": default_name,
                    }
                )

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
    try:
        # Get the workflow file path
        workflow_path = os.path.join(os.path.dirname(__file__), "workflows", filename)

        # Check if the file exists
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")

        # Create a temporary flowchart file for the agent to use
        flowchart_dir = os.path.join(os.path.dirname(__file__), "flowcharts")
        os.makedirs(flowchart_dir, exist_ok=True)
        flowchart_path = os.path.join(flowchart_dir, "current_flowchart.yaml")

        # Read the workflow file
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        # Write to the current_flowchart.yaml file
        with open(flowchart_path, "w", encoding="utf-8") as f:
            yaml.dump(workflow_data, f)

        # Create the agent
        agent = PlanAndExecuteAgent()

        # Execute the workflow
        result = await agent.run(request.input, request.config)

        return {
            "final_result": result.get("final_result", ""),
            "goal_assessment_result": result.get("goal_assessment_result"),
            "goal_assessment_feedback": result.get("goal_assessment_feedback"),
            "error": result.get("error"),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
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

        # Read and parse the workflow file
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        # Create or update the metadata section
        if "metadata" not in workflow_data or not isinstance(workflow_data["metadata"], dict):
            workflow_data["metadata"] = {}

        workflow_data["metadata"]["name"] = request.name

        # Write the updated workflow data back to the file
        with open(workflow_path, "w", encoding="utf-8") as f:
            yaml.dump(workflow_data, f)

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
