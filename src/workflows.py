#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Workflow handling logic for the API server."""

import os
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from tinydb import TinyDB, Query


def delete_workflow(filename: str) -> Dict[str, Any]:
    """
    Delete a workflow from the database.

    Args:
        filename: The name or ID of the workflow to delete

    Returns:
        A dictionary indicating success or failure
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")
        Workflow = Query()

        # Extract workflow ID from filename if it's a filename
        workflow_id = filename

        # Check if the workflow exists
        workflow = workflows_table.get(Workflow.id == workflow_id)
        if not workflow:
            return {"success": False, "message": f"Workflow '{workflow_id}' not found"}

        # Delete the workflow
        workflows_table.remove(Workflow.id == workflow_id)

        return {"success": True, "message": f"Workflow '{workflow_id}' deleted successfully"}

    except Exception as e:
        return {"success": False, "message": f"An error occurred while deleting workflow: {str(e)}"}


async def load_flowchart(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a flowchart from a workflow ID.

    Args:
        workflow_id: ID of the workflow to load

    Returns:
        The flowchart data as a dictionary, or None if it doesn't exist
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")
        Workflow = Query()

        # Get the workflow from database
        return workflows_table.get(Workflow.id == workflow_id)
    except Exception:
        return None


def save_workflow(content: bytes, workflow_id: str = None) -> Tuple[bool, str, str]:
    """
    Validate and save a workflow.

    Args:
        content: The workflow content as bytes
        workflow_id: Optional workflow ID to use (if None, will be derived from metadata)

    Returns:
        A tuple containing (success, message, saved_filename)
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")
        current_workflow_table = db.table("current_workflow")

        # Parse the content to validate it
        try:
            # Parse the JSON content
            flowchart_data = json.loads(content)

            # Validate flowchart name
            if not flowchart_data.get("metadata", {}).get("name"):
                return False, "Flowchart must have a name in metadata", ""

            # Validate node commands
            for node in flowchart_data.get("nodes", []):
                # For action nodes, ensure they have a prompt field that's not None
                if node.get("type") == "act" and ("prompt" not in node or node.get("prompt") is None):
                    # Check if the node has a command
                    if "id" in node:
                        return False, f"Node {node['id']} must have a command", ""
                    else:
                        return False, "Action nodes must have a command", ""
                    # Add an empty prompt field if it's missing or None
                    node["prompt"] = ""
        except Exception as e:
            return False, f"Invalid workflow format: {str(e)}", ""

        # Get the flowchart name from metadata
        flowchart_name = flowchart_data.get("metadata", {}).get("name", "Untitled")

        # Create a safe ID from the flowchart name if not provided
        if not workflow_id:
            workflow_id = "".join(c if c.isalnum() else "_" for c in flowchart_name)
        else:
            workflow_id = workflow_id

        # Add timestamp and ID to the workflow data
        flowchart_data["id"] = workflow_id
        flowchart_data["updated_at"] = datetime.now().isoformat()

        # Check if the workflow already exists
        Workflow = Query()
        existing = workflows_table.get(Workflow.id == workflow_id)
        if existing:
            # Update the existing workflow
            workflows_table.update(flowchart_data, Workflow.id == workflow_id)
        else:
            # Insert a new workflow
            flowchart_data["created_at"] = datetime.now().isoformat()
            workflows_table.insert(flowchart_data)

        # Also save as current workflow
        current_workflow_table.truncate()  # Clear the current workflow table
        current_workflow_table.insert(flowchart_data)

        # Return the workflow ID
        safe_filename = workflow_id

        # Return success
        return True, f"Flowchart '{flowchart_name}' saved successfully", safe_filename

    except Exception as e:
        return False, f"An error occurred: {str(e)}", ""


def extract_workflow_metadata(workflow_id: str) -> dict:
    """
    Extract metadata from a workflow.

    Args:
        workflow_id: ID of the workflow

    Returns:
        A dictionary containing metadata (name, description)
    """
    metadata = {"name": "", "description": ""}

    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")
        Workflow = Query()

        # Try to get workflow from database
        content = workflows_table.get(Workflow.id == workflow_id)

        if content:
            # Check if metadata section exists
            if "metadata" in content and isinstance(content["metadata"], dict):
                if "name" in content["metadata"]:
                    metadata["name"] = content["metadata"]["name"]
                if "description" in content["metadata"]:
                    metadata["description"] = content["metadata"]["description"]

            # If no description in metadata, get the first node with content as a description
            if not metadata["description"] and "nodes" in content and content["nodes"]:
                for node in content["nodes"]:
                    if node.get("content"):
                        metadata["description"] = node["content"]
                        break
    except Exception:
        pass

    return metadata


def update_workflow_name(workflow_id: str, new_name: str) -> Dict[str, Any]:
    """
    Update the name of a workflow in its metadata.

    Args:
        workflow_id: ID of the workflow to update
        new_name: The new name to set for the workflow

    Returns:
        A dictionary indicating success or failure
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")
        current_workflow_table = db.table("current_workflow")
        Workflow = Query()

        # Get the workflow from database
        workflow = workflows_table.get(Workflow.id == workflow_id)
        if not workflow:
            return {"success": False, "message": f"Workflow '{workflow_id}' not found"}

        # Create or update the metadata section
        if "metadata" not in workflow or not isinstance(workflow["metadata"], dict):
            workflow["metadata"] = {}

        workflow["metadata"]["name"] = new_name
        workflow["updated_at"] = datetime.now().isoformat()

        # Update the workflow in the database
        workflows_table.update(workflow, Workflow.id == workflow_id)

        # If this is the current workflow, update it too
        current = current_workflow_table.all()
        if current and current[0].get("id") == workflow_id:
            current_workflow_table.update(workflow, Workflow.id == workflow_id)

        return {"success": True, "message": "Workflow name updated successfully"}

    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}


async def list_workflows() -> List[Dict[str, Any]]:
    """
    List all available workflows from the database.

    Returns:
        A list of workflow information including name, filename, and description.
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        workflows_table = db.table("workflows")

        # Get all workflows from the database
        all_workflows = workflows_table.all()

        # Format the workflow information
        workflows = []
        for workflow in all_workflows:
            # Get basic workflow info
            workflow_id = workflow.get("id", "")

            # Get metadata
            metadata = workflow.get("metadata", {})
            display_name = metadata.get("name", workflow_id)
            description = metadata.get("description", "")

            # Add to the list
            workflows.append(
                {
                    "name": display_name,
                    "filename": workflow_id,  # For backward compatibility
                    "id": workflow_id,
                    "description": description,
                    "default_name": workflow_id,
                    "created_at": workflow.get("created_at"),
                    "updated_at": workflow.get("updated_at"),
                }
            )

        return workflows

    except Exception as e:
        # Re-raise the exception to be handled by the caller
        raise e


async def load_current_workflow() -> Optional[Dict[str, Any]]:
    """
    Load the current workflow from the database.

    Returns:
        The current workflow data as a dictionary, or None if it doesn't exist
    """
    try:
        # Initialize the database
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        db = TinyDB(db_path)
        current_workflow_table = db.table("current_workflow")

        current = current_workflow_table.all()
        if current:
            return current[0]
        return None
    except Exception:
        return None
