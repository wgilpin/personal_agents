"""Tests for the API server"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from api_server import api
from workflows import extract_workflow_metadata

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
            {"id": "node1", "type": "act", "prompt": "Search for information"},
            {"id": "node2", "type": "choice", "prompt": "Is the information complete?"},
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
            {"id": "node1", "type": "act", "prompt": "First action"},
            {"id": "node2", "type": "choice", "prompt": "Make a decision"},
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
async def test_execute_workflow(mock_agent_class, mock_workflow_filename):
    """Test the execute_workflow endpoint"""
    # Create a mock agent instance
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value={
            "final_result": None,
            "goal_assessment_result": None,
            "goal_assessment_feedback": None,
            "error": None,
        }
    )
    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input", "config": {"recursion_limit": 10}}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_workflow_filename}/execute", json=request_data)

    # Check the response
    assert response.status_code == 200
    response_data = response.json()
    # The final_result is a JSON string with a response_text field
    assert json.loads(response_data["final_result"]) == {"response_text": None}
    assert response_data["goal_assessment_result"] is None
    assert response_data["goal_assessment_feedback"] is None
    assert response_data["error"] is None

    # Verify that the agent was called with the correct parameters
    # The agent is called once for each node in the workflow
    # The first call includes the input from the request with context
    mock_agent.run.assert_any_call(
        "Search for information\nContext from previous steps: Test input", {"recursion_limit": 10}
    )
    assert mock_agent.run.call_count == 2


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
async def test_execute_workflow_agent_error(mock_agent_class, mock_workflow_filename):
    """Test the execute_workflow endpoint when the agent raises an error"""
    # Create a mock agent instance that raises an error
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=Exception("Test error"))
    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_workflow_filename}/execute", json=request_data)

    # Check the response
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_current_flowchart_traverses_nodes(mock_agent_class):
    """Test that execute_current_flowchart traverses nodes in the flowchart"""
    # Define the path to the test flowchart file
    flowcharts_dir = os.path.join(os.path.dirname(__file__), "flowcharts")
    os.makedirs(flowcharts_dir, exist_ok=True)
    test_flowchart_path = os.path.join(flowcharts_dir, "current_flowchart.yaml")

    # Create a test flowchart with multiple nodes and connections
    test_flowchart = {
        "metadata": {"name": "Multi-Node Test Flowchart"},
        "nodes": [
            {"id": "node-1", "type": "act", "position": {"x": 100, "y": 100}, "prompt": "First node prompt"},
            {"id": "node-2", "type": "act", "position": {"x": 300, "y": 300}, "prompt": "Second node prompt"},
        ],
        "connections": [
            {"from": {"nodeId": "node-1", "position": "bottom"}, "to": {"nodeId": "node-2", "position": "top"}},
        ],
    }

    # Write the test flowchart to the file
    with open(test_flowchart_path, "w", encoding="utf-8") as f:
        yaml.dump(test_flowchart, f)

    try:
        # Create a mock agent instance with different responses for each call
        mock_agent = MagicMock()

        # Set up the mock to return different values for each call
        mock_agent.run = AsyncMock()
        mock_agent.run.side_effect = [
            # First node result
            {
                "final_result": "First node result",
                "goal_assessment_result": None,
                "goal_assessment_feedback": None,
                "error": None,
            },
            # Second node result
            {
                "final_result": "Second node result",
                "goal_assessment_result": None,
                "goal_assessment_feedback": None,
                "error": None,
            },
        ]

        mock_agent_class.return_value = mock_agent

        # Create a test request
        request_data = {"input": "Test input"}

        # Send a request to the endpoint
        response = client.post("/flowchart/current/execute", json=request_data)

        # Check the response
        assert response.status_code == 200
        assert "Second node result" in response.json()["final_result"]
    finally:
        # Clean up the test file after the test
        if os.path.exists(test_flowchart_path):
            os.remove(test_flowchart_path)


def test_extract_workflow_metadata(mock_workflow_with_metadata_filename):
    """Test extracting metadata from a workflow file"""
    # Get the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    test_workflow_path = os.path.join(workflows_dir, mock_workflow_with_metadata_filename)

    # Extract metadata from the workflow file
    metadata = extract_workflow_metadata(test_workflow_path)

    # Check that the metadata was extracted correctly
    assert metadata["name"] == "Custom Workflow Name"
    assert metadata["description"] == "Custom workflow description"


def test_list_workflows_with_custom_names(mock_workflow_with_metadata_filename):
    """Test listing workflows with custom names"""
    # Send a request to the list_workflows endpoint
    response = client.get("/workflows")

    # Check the response
    assert response.status_code == 200
    workflows = response.json()

    # Find the test workflow in the list
    test_workflow = next((w for w in workflows if w["filename"] == mock_workflow_with_metadata_filename), None)

    # Check that the workflow was found and has the correct name
    assert test_workflow is not None
    assert test_workflow["name"] == "Custom Workflow Name"
    assert test_workflow["default_name"] == "test_workflow_with_metadata"


def test_update_workflow_name(mock_workflow_filename):
    """Test updating a workflow name"""
    # Define the new name
    new_name = "Updated Workflow Name"

    # Send a request to update the workflow name
    response = client.put(f"/workflows/{mock_workflow_filename}/name", json={"name": new_name})

    # Check the response
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Get the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    test_workflow_path = os.path.join(workflows_dir, mock_workflow_filename)

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
    test_workflow = next((w for w in workflows if w["filename"] == mock_workflow_filename), None)
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
