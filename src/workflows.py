#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Workflow handling logic for the API server."""

import os
import yaml
from typing import Dict, Any, Tuple, Optional, List


async def load_flowchart_from_yaml(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a flowchart from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        The flowchart data as a dictionary, or None if the file doesn't exist or is invalid
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return None

        # Read and parse the flowchart file
        with open(file_path, "r", encoding="utf-8") as f:
            flowchart_data = yaml.safe_load(f)

        return flowchart_data
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

        # Save the file to the workflows directory
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        os.makedirs(workflows_dir, exist_ok=True)

        # Get the flowchart name from metadata
        flowchart_name = flowchart_data.get("metadata", {}).get("name", "Untitled")

        # Create a safe filename from the flowchart name if not provided
        if not filename:
            safe_filename = "".join(c if c.isalnum() else "_" for c in flowchart_name) + ".yaml"
        else:
            safe_filename = filename

        # Save the file with its name in the workflows directory
        workflow_path = os.path.join(workflows_dir, safe_filename)

        # Also save as current_flowchart.yaml in the workflows directory for backward compatibility
        current_flowchart_path = os.path.join(workflows_dir, "current_flowchart.yaml")

        with open(workflow_path, "wb") as f:
            f.write(content)

        # Also save as current_flowchart.yaml for backward compatibility
        with open(current_flowchart_path, "wb") as f:
            f.write(content)

        return True, f"Flowchart '{flowchart_name}' saved successfully", safe_filename

    except Exception as e:
        return False, f"An error occurred: {str(e)}", ""


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


def update_workflow_name(file_path: str, new_name: str) -> Dict[str, Any]:
    """
    Update the name of a workflow in its metadata.

    Args:
        file_path: Path to the workflow file
        new_name: The new name to set for the workflow

    Returns:
        A dictionary indicating success or failure
    """
    try:
        # Read and parse the workflow file
        with open(file_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        # Create or update the metadata section
        if "metadata" not in workflow_data or not isinstance(workflow_data["metadata"], dict):
            workflow_data["metadata"] = {}

        workflow_data["metadata"]["name"] = new_name

        # Write the updated workflow data back to the file
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(workflow_data, f)

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
        # Re-raise the exception to be handled by the caller
        raise e
