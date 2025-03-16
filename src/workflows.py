#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Workflow handling logic for the API server."""

import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from tinydb import TinyDB, Query
import yaml


def delete_workflow(filename: str) -> Dict[str, Any]:
    """
    Delete a workflow file from the workflows directory.

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
        workflow_id = os.path.splitext(filename)[0] if filename.endswith((".yaml", ".yml")) else filename

        # Check if the workflow exists
        workflow = workflows_table.get(Workflow.id == workflow_id)
        if not workflow:
            return {"success": False, "message": f"Workflow '{workflow_id}' not found"}

        # Delete the workflow
        workflows_table.remove(Workflow.id == workflow_id)

        return {"success": True, "message": f"Workflow '{workflow_id}' deleted successfully"}

    except Exception as e:
        return {"success": False, "message": f"An error occurred while deleting workflow: {str(e)}"}


async def load_flowchart_from_yaml(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a flowchart from a YAML file.

    Args:
        file_path: Path to the YAML file or workflow ID

    Returns:
        The flowchart data as a dictionary, or None if the file doesn't exist or is invalid
    """
    try:
        # If it's a file path, load from file
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                flowchart_data = yaml.safe_load(f)
            return flowchart_data
        else:
            # Try to load from database
            db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
            db = TinyDB(db_path)
            workflows_table = db.table("workflows")
            Workflow = Query()

            workflow_id = os.path.basename(file_path)
            return workflows_table.get(Workflow.id == workflow_id)
    except Exception:
        return None


def save_workflow_from_yaml(content: bytes, filename: str = None) -> Tuple[bool, str, str]:
    """
    Validate and save a YAML workflow file.

    Args:
        content: The YAML content as bytes
        filename: Optional filename to use (if None, will be derived from metadata)

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

        # Parse the YAML content to validate it
        try:
            flowchart_data = yaml.safe_load(content)

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
        except yaml.YAMLError as e:
            return False, f"Invalid YAML format: {str(e)}", ""

        # Get the flowchart name from metadata
        flowchart_name = flowchart_data.get("metadata", {}).get("name", "Untitled")

        # Create a safe ID from the flowchart name if not provided
        if not filename:
            workflow_id = "".join(c if c.isalnum() else "_" for c in flowchart_name)
        else:
            workflow_id = os.path.splitext(filename)[0]

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

        # For backward compatibility, also save to files
        # This can be removed once the migration is complete
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        safe_filename = f"{workflow_id}.yaml"

        # Return success
        return True, f"Flowchart '{flowchart_name}' saved successfully", safe_filename

    except Exception as e:
        return False, f"An error occurred: {str(e)}", ""


def extract_workflow_metadata(file_path: str) -> dict:
    """
    Extract metadata from a workflow file.

    Args:
        file_path: Path to the workflow file or workflow ID

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

        # Try to get workflow from database first
        workflow_id = os.path.splitext(os.path.basename(file_path))[0]
        content = workflows_table.get(Workflow.id == workflow_id)

        # If not found in database, try to read from file
        if not content and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

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


def update_workflow_name(file_path: str, new_name: str) -> Dict[str, Any]:
    """
    Update the name of a workflow in its metadata.

    Args:
        file_path: Path to the workflow file or workflow ID
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

        # Extract workflow ID from file path
        workflow_id = os.path.splitext(os.path.basename(file_path))[0]

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
        return {"success": False, "message": f"An error occurred while updating workflow name: {str(e)}"}


async def list_workflows() -> List[Dict[str, Any]]:
    """
    List all available workflows from the workflows directory.

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
                    "filename": f"{workflow_id}.yaml",  # For backward compatibility
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


# Migration function to convert existing YAML files to TinyDB
def migrate_yaml_to_tinydb() -> Dict[str, Any]:
    """
    Migrate existing YAML workflow files to TinyDB.

    Returns:
        A dictionary with migration statistics
    """
    try:
        # Get the workflows directory path
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")

        # Check if the directory exists
        if not os.path.exists(workflows_dir):
            return {"success": True, "message": "No workflows directory found, nothing to migrate", "migrated": 0}

        # Count of migrated workflows
        migrated_count = 0

        # List all YAML files in the directory
        for filename in os.listdir(workflows_dir):
            if filename.endswith((".yaml", ".yml")):
                file_path = os.path.join(workflows_dir, filename)

                # Read the workflow file
                with open(file_path, "rb") as f:
                    content = f.read()

                # Save to TinyDB
                success, _, _ = save_workflow_from_yaml(content, filename)
                if success:
                    migrated_count += 1

        return {
            "success": True,
            "message": f"Successfully migrated {migrated_count} workflows to TinyDB",
            "migrated": migrated_count,
        }

    except Exception as e:
        return {"success": False, "message": f"Migration failed: {str(e)}", "migrated": 0}
