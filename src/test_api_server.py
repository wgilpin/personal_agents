"""Tests for the API server"""

import json
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api_server import api, WorkflowExecuteRequest, extract_workflow_metadata


# Create a test client
client = TestClient(api)


@pytest.fixture
def mock_workflow_file():
    """Create a mock workflow file for testing"""
    # Define the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    test_workflow_path = os.path.join(workflows_dir, "test_workflow.yaml")

    # Create a simple test workflow
    test_workflow = {
        "nodes": [
            {"id": "node1", "type": "act", "content": "Search for information"},
            {"id": "node2", "type": "choice", "content": "Is the information complete?"},
        ],
        "connections": [
            {"from": {"nodeId": "node1"}, "to": {"nodeId": "node2"}},
        ],
    }

    # Write the test workflow to a file
    with open(test_workflow_path, "w", encoding="utf-8") as f:
        yaml.dump(test_workflow, f)

    yield "test_workflow.yaml"

    # Clean up the test file after the test
    if os.path.exists(test_workflow_path):
        os.remove(test_workflow_path)


@pytest.fixture
def mock_workflow_with_metadata():
    """Create a mock workflow file with metadata for testing"""
    # Define the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    test_workflow_path = os.path.join(workflows_dir, "test_workflow_with_metadata.yaml")

    # Create a test workflow with metadata
    test_workflow = {
        "metadata": {"name": "Custom Workflow Name", "description": "Custom workflow description"},
        "nodes": [
            {"id": "node1", "type": "act", "content": "First action"},
            {"id": "node2", "type": "choice", "content": "Make a decision"},
        ],
        "connections": [
            {"from": {"nodeId": "node1"}, "to": {"nodeId": "node2"}},
        ],
    }

    # Write the test workflow to a file
    with open(test_workflow_path, "w", encoding="utf-8") as f:
        yaml.dump(test_workflow, f)

    yield "test_workflow_with_metadata.yaml"

    # Clean up the test file after the test
    if os.path.exists(test_workflow_path):
        os.remove(test_workflow_path)


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow(mock_agent_class, mock_workflow_file):
    """Test the execute_workflow endpoint"""
    # Create a mock agent instance
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value={
            "final_result": "Test result",
            "goal_assessment_result": json.dumps(["Test item 1", "Test item 2"]),
            "goal_assessment_feedback": None,
            "error": None,
        }
    )
    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input", "config": {"recursion_limit": 10}}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_workflow_file}/execute", json=request_data)

    # Check the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["final_result"] == "Test result"
    assert response_data["goal_assessment_result"] == json.dumps(["Test item 1", "Test item 2"])
    assert response_data["goal_assessment_feedback"] is None
    assert response_data["error"] is None

    # Verify that the agent was called with the correct parameters
    mock_agent.run.assert_called_once_with("Test input", {"recursion_limit": 10})


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow_file_not_found(mock_agent_class):
    """Test the execute_workflow endpoint with a non-existent workflow file"""
    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint with a non-existent workflow file
    response = client.post("/workflows/non_existent_workflow.yaml/execute", json=request_data)

    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

    # Verify that the agent was not created
    mock_agent_class.assert_not_called()


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow_agent_error(mock_agent_class, mock_workflow_file):
    """Test the execute_workflow endpoint when the agent raises an error"""
    # Create a mock agent instance that raises an error
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=Exception("Test error"))
    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_workflow_file}/execute", json=request_data)

    # Check the response
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


def test_extract_workflow_metadata(mock_workflow_with_metadata):
    """Test extracting metadata from a workflow file"""
    # Get the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    test_workflow_path = os.path.join(workflows_dir, mock_workflow_with_metadata)

    # Extract metadata from the workflow file
    metadata = extract_workflow_metadata(test_workflow_path)

    # Check that the metadata was extracted correctly
    assert metadata["name"] == "Custom Workflow Name"
    assert metadata["description"] == "Custom workflow description"


def test_list_workflows_with_custom_names(mock_workflow_with_metadata):
    """Test listing workflows with custom names"""
    # Send a request to the list_workflows endpoint
    response = client.get("/workflows")

    # Check the response
    assert response.status_code == 200
    workflows = response.json()

    # Find the test workflow in the list
    test_workflow = next((w for w in workflows if w["filename"] == mock_workflow_with_metadata), None)

    # Check that the workflow was found and has the correct name
    assert test_workflow is not None
    assert test_workflow["name"] == "Custom Workflow Name"
    assert test_workflow["default_name"] == "test_workflow_with_metadata"


def test_update_workflow_name(mock_workflow_file):
    """Test updating a workflow name"""
    # Define the new name
    new_name = "Updated Workflow Name"

    # Send a request to update the workflow name
    response = client.put(f"/workflows/{mock_workflow_file}/name", json={"name": new_name})

    # Check the response
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Get the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    test_workflow_path = os.path.join(workflows_dir, mock_workflow_file)

    # Read the updated workflow file
    with open(test_workflow_path, "r", encoding="utf-8") as f:
        workflow_data = yaml.safe_load(f)

    # Check that the name was updated in the file
    assert "metadata" in workflow_data
    assert workflow_data["metadata"]["name"] == new_name

    # Send a request to the list_workflows endpoint
    response = client.get("/workflows")

    # Check that the updated name is returned in the list
    workflows = response.json()
    test_workflow = next((w for w in workflows if w["filename"] == mock_workflow_file), None)
    assert test_workflow is not None
    assert test_workflow["name"] == new_name


@pytest.mark.asyncio
async def test_upload_flowchart_missing_name():
    """Test uploading a flowchart without a name in metadata"""
    flowchart_data = {"nodes": [{"id": "node1", "type": "act", "prompt": "echo Hello World"}], "connections": []}
    response = client.post(
        "/flowchart", files={"file": ("flowchart.yaml", yaml.dump(flowchart_data), "application/x-yaml")}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Flowchart must have a name in metadata"


@pytest.mark.asyncio
async def test_upload_flowchart_missing_command():
    """Test uploading a flowchart with an action node missing a command"""
    flowchart_data = {
        "metadata": {"name": "Test Flowchart"},
        "nodes": [{"id": "node1", "type": "act"}],
        "connections": [],
    }
    response = client.post(
        "/flowchart", files={"file": ("flowchart.yaml", yaml.dump(flowchart_data), "application/x-yaml")}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Node node1 must have a command"


if __name__ == "__main__":
    pytest.main(["-xvs", "test_api_server.py"])
