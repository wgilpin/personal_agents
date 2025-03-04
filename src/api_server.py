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

        # Parse the YAML content to validate it
        try:
            flowchart_data = yaml.safe_load(content)
            # Validate flowchart name
            if not flowchart_data.get("metadata", {}).get("name"):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Flowchart must have a name in metadata"},
                )
            # Validate node commands
            for node in flowchart_data.get("nodes", []):
                # For action nodes, ensure they have a prompt field that's not None
                if node.get("type") == "act" and ("prompt" not in node or node.get("prompt") is None):
                    # Add an empty prompt field if it's missing or None
                    node["prompt"] = ""
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


@api.get("/flowchart/current", response_model=Dict[str, Any])
async def get_current_flowchart() -> Dict[str, Any]:
    """
    Get the current flowchart from the flowcharts directory.

    Returns:
        The current flowchart data.
    """
    try:
        # Get the flowchart file path
        flowchart_path = os.path.join(os.path.dirname(__file__), "flowcharts", "current_flowchart.yaml")

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
    try:
        # Get the flowchart file path
        flowchart_path = os.path.join(os.path.dirname(__file__), "flowcharts", "current_flowchart.yaml")

        # Check if the file exists
        if not os.path.exists(flowchart_path):
            raise HTTPException(status_code=404, detail="Current flowchart not found")

        # Load the flowchart file
        with open(flowchart_path, "r", encoding="utf-8") as f:
            flowchart_data = yaml.safe_load(f)

        # Initialize variables to store results
        final_result = ""
        error = None

        try:
            # Get the nodes and connections from the flowchart
            nodes = flowchart_data.get("nodes", [])
            connections = flowchart_data.get("connections", [])

            if not nodes:
                raise ValueError("Flowchart has no nodes")

            # Find start node (node with type 'start') or use the first node
            current_node = None
            for node in nodes:
                if node.get("type") == "start":
                    current_node = node
                    break

            # If no start node found, use the first node
            if not current_node:
                current_node = nodes[0]

            # Create a map of node IDs to nodes for easy lookup
            node_map = {node["id"]: node for node in nodes}

            # Create a map of connections for easy lookup
            connection_map = {}
            if connections:
                for conn in connections:
                    from_id = conn.get("from", {}).get("nodeId")
                    from_pos = conn.get("from", {}).get("position")
                    to_id = conn.get("to", {}).get("nodeId")

                    if from_id not in connection_map:
                        connection_map[from_id] = {}

                    connection_map[from_id][from_pos] = to_id

            # Process nodes until we reach a terminal node or have no more connections
            while current_node:
                node_id = current_node["id"]
                node_type = current_node.get("type")
                node_prompt = current_node.get("prompt", "")
                node_content = current_node.get("content", "")

                print(f"Processing node: {node_id}, type: {node_type}")

                if node_type == "act":
                    # For action nodes, use plan_and_execute to run just this node
                    agent = PlanAndExecuteAgent()

                    # Combine the node prompt with the user input
                    combined_input = f"{node_prompt}\n\nUser input: {request.input}"

                    # Execute the agent with just this single action node
                    result = await agent.run(combined_input, request.config)

                    # Add the result to the final result
                    if result.get("final_result"):
                        node_result = result["final_result"]
                        final_result += f"Node {node_id} ({node_content}): {node_result}\n"
                        print(f"Node {node_id} result: {node_result}")

                elif node_type == "choice":
                    # For choice nodes, make a simple LLM call to determine which path to take
                    from langchain_openai import ChatOpenAI

                    # Create a simple LLM
                    llm = ChatOpenAI(model="gpt-4o")

                    # Combine the node prompt with the user input
                    combined_input = f"{node_prompt}\n\nUser input: {request.input}\n\nBased on the above, respond with 'true' or 'false'."

                    # Make the LLM call
                    response = await llm.ainvoke(combined_input)
                    choice_result = response.content.strip().lower()

                    # Add the choice result to the final result
                    final_result += f"Node {node_id} ({node_content}): Decision is {choice_result}\n"
                    print(f"Node {node_id} choice: {choice_result}")

                elif node_type == "terminal":
                    # Terminal node, add its content to the result and end the workflow
                    final_result += f"Node {node_id} ({node_content}): Workflow completed\n"
                    print(f"Terminal node {node_id} reached")
                    break

                # Determine the next node to process
                next_node_id = None
                if node_id in connection_map:
                    if node_type == "choice":
                        # For choice nodes, follow the true/false path
                        if "true" in choice_result and "true" in connection_map[node_id]:
                            next_node_id = connection_map[node_id]["true"]
                        elif "false" in choice_result and "false" in connection_map[node_id]:
                            next_node_id = connection_map[node_id]["false"]
                        else:
                            # If no matching position, try to use any available connection
                            for pos, to_id in connection_map[node_id].items():
                                next_node_id = to_id
                                break
                    else:
                        # For other nodes, follow the first connection
                        for pos, to_id in connection_map[node_id].items():
                            next_node_id = to_id
                            break

                # Move to the next node if it exists
                if next_node_id and next_node_id in node_map:
                    current_node = node_map[next_node_id]
                    print(f"Moving to next node: {next_node_id}")
                else:
                    print(f"No next node found, ending workflow")
                    current_node = None

        except Exception as e:
            error = f"Error during flowchart execution: {str(e)}"
            print(f"\n\n{error}")

        return {
            "final_result": final_result,
            "error": error,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle all other exceptions
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

        # Load the workflow file
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        # Initialize variables to store results
        final_result = ""
        error = None

        try:
            # Get the nodes and connections from the workflow
            nodes = workflow_data.get("nodes", [])
            connections = workflow_data.get("connections", [])

            if not nodes:
                raise ValueError("Workflow has no nodes")

            # Find start node (node with type 'start') or use the first node
            current_node = None
            for node in nodes:
                if node.get("type") == "start":
                    current_node = node
                    break

            # If no start node found, use the first node
            if not current_node:
                current_node = nodes[0]

            # Create a map of node IDs to nodes for easy lookup
            node_map = {node["id"]: node for node in nodes}

            # Create a map of connections for easy lookup
            connection_map = {}
            if connections:
                for conn in connections:
                    from_id = conn.get("from", {}).get("nodeId")
                    from_pos = conn.get("from", {}).get("position")
                    to_id = conn.get("to", {}).get("nodeId")

                    if from_id not in connection_map:
                        connection_map[from_id] = {}

                    connection_map[from_id][from_pos] = to_id

            # Process nodes until we reach a terminal node or have no more connections
            while current_node:
                node_id = current_node["id"]
                node_type = current_node.get("type")
                node_prompt = current_node.get("prompt", "")
                node_content = current_node.get("content", "")

                print(f"Processing node: {node_id}, type: {node_type}")

                if node_type == "act":
                    # For action nodes, use plan_and_execute to run just this node
                    agent = PlanAndExecuteAgent()

                    # Combine the node prompt with the user input
                    combined_input = f"{node_prompt}\n\nUser input: {request.input}"

                    # Execute the agent with just this single action node
                    result = await agent.run(combined_input, request.config)

                    # Add the result to the final result
                    if result.get("final_result"):
                        node_result = result["final_result"]
                        final_result += f"Node {node_id} ({node_content}): {node_result}\n"
                        print(f"Node {node_id} result: {node_result}")

                elif node_type == "choice":
                    # For choice nodes, make a simple LLM call to determine which path to take
                    from langchain_openai import ChatOpenAI

                    # Create a simple LLM
                    llm = ChatOpenAI(model="gpt-4o")

                    # Combine the node prompt with the user input
                    combined_input = f"{node_prompt}\n\nUser input: {request.input}\n\nBased on the above, respond with 'true' or 'false'."

                    # Make the LLM call
                    response = await llm.ainvoke(combined_input)
                    choice_result = response.content.strip().lower()

                    # Add the choice result to the final result
                    final_result += f"Node {node_id} ({node_content}): Decision is {choice_result}\n"
                    print(f"Node {node_id} choice: {choice_result}")

                elif node_type == "terminal":
                    # Terminal node, add its content to the result and end the workflow
                    final_result += f"Node {node_id} ({node_content}): Workflow completed\n"
                    print(f"Terminal node {node_id} reached")
                    break

                # Determine the next node to process
                next_node_id = None
                if node_id in connection_map:
                    if node_type == "choice":
                        # For choice nodes, follow the true/false path
                        if "true" in choice_result and "true" in connection_map[node_id]:
                            next_node_id = connection_map[node_id]["true"]
                        elif "false" in choice_result and "false" in connection_map[node_id]:
                            next_node_id = connection_map[node_id]["false"]
                        else:
                            # If no matching position, try to use any available connection
                            for pos, to_id in connection_map[node_id].items():
                                next_node_id = to_id
                                break
                    else:
                        # For other nodes, follow the first connection
                        for pos, to_id in connection_map[node_id].items():
                            next_node_id = to_id
                            break

                # Move to the next node if it exists
                if next_node_id and next_node_id in node_map:
                    current_node = node_map[next_node_id]
                    print(f"Moving to next node: {next_node_id}")
                else:
                    print(f"No next node found, ending workflow")
                    current_node = None

        except Exception as e:
            error = f"Error during workflow execution: {str(e)}"
            print(f"\n\n{error}")

        return {
            "final_result": final_result,
            "error": error,
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
