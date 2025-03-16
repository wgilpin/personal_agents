"""Tests for the API server"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from tinydb import TinyDB, Query

from api_server import api
from workflows import extract_workflow_metadata

# Create a test client
client = TestClient(api)


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing"""
    # Initialize the database
    db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = TinyDB(db_path)
    workflows_table = db.table("workflows")
    Workflow = Query()

    # Create a simple test workflow
    test_workflow = {
        "metadata": {"name": "Test Workflow"},
        "nodes": [
            {"id": "node1", "type": "act", "prompt": "Search for information"},
            {"id": "node2", "type": "choice", "prompt": "Is the information complete?"},
        ],
        "connections": [
            {"from": {"nodeId": "node1"}, "to": {"nodeId": "node2"}},
        ],
    }

    # Add ID and timestamps
    workflow_id = "test_workflow"
    test_workflow["id"] = workflow_id
    test_workflow["created_at"] = datetime.now().isoformat()
    test_workflow["updated_at"] = datetime.now().isoformat()

    # Save to TinyDB
    current_workflow_table = db.table("current_workflow")
    current_workflow_table.truncate()
    current_workflow_table.insert(test_workflow)
    workflows_table.upsert(test_workflow, Workflow.id == workflow_id)

    yield "test_workflow"

    # Clean up the database after the test


#    current_workflow_table.truncate()
#    workflows_table.remove(Workflow.id == workflow_id)


@pytest.fixture
def mock_workflow_with_metadata():
    """Create a mock workflow with metadata for testing"""
    # Initialize the database
    db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = TinyDB(db_path)
    workflows_table = db.table("workflows")
    Workflow = Query()

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

    # Add ID and timestamps
    workflow_id = "test_workflow_with_metadata"
    test_workflow["id"] = workflow_id
    test_workflow["created_at"] = datetime.now().isoformat()
    test_workflow["updated_at"] = datetime.now().isoformat()

    # Save to TinyDB
    workflows_table.upsert(test_workflow, Workflow.id == workflow_id)

    yield "test_workflow_with_metadata"

    # Clean up the database after the test
    workflows_table.remove(Workflow.id == workflow_id)

    # Also clean up any data that might have been created for backward compatibility
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    test_workflow_path = os.path.join(workflows_dir, "test_workflow_with_metadata")
    if os.path.exists(test_workflow_path):
        os.remove(test_workflow_path)


@pytest.fixture
def mock_workflow_id():
    """Provide a mock workflow ID for testing"""
    yield "test_workflow"


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow(mock_agent_class, mock_workflow, mock_workflow_id):
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
    response = client.post(f"/workflows/{mock_workflow_id}/execute", json=request_data)

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
    """Test the execute_workflow endpoint with a non-existent workflow"""
    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint with a non-existent workflow
    response = client.post("/workflows/non_existent_workflow/execute", json=request_data)

    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

    # Verify that the agent was not created
    mock_agent_class.assert_not_called()


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow_agent_error(mock_agent_class, mock_workflow_id):
    """Test the execute_workflow endpoint when the agent raises an error"""
    # Create a mock agent instance that raises an error
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=Exception("Test error"))
    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_workflow_id}/execute", json=request_data)

    # Check the response
    assert response.status_code == 500
    assert "error occurred" in response.json()["detail"]


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_current_flowchart_traverses_nodes(mock_agent_class):
    """Test that execute_current_flowchart traverses nodes in the flowchart"""
    # Initialize the database for the test flowchart
    # Initialize the database
    db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = TinyDB(db_path)
    current_workflow_table = db.table("current_workflow")
    workflows_table = db.table("workflows")

    # Create a test flowchart with multiple nodes and connections
    test_flowchart = {
        "metadata": {"name": "Multi-Node Test Flowchart"},
        "id": "current_flowchart",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "nodes": [
            {"id": "node-1", "type": "act", "position": {"x": 100, "y": 100}, "prompt": "First node prompt"},
            {"id": "node-2", "type": "act", "position": {"x": 300, "y": 300}, "prompt": "Second node prompt"},
        ],
        "connections": [
            {"from": {"nodeId": "node-1", "position": "bottom"}, "to": {"nodeId": "node-2", "position": "top"}},
        ],
    }

    # Save to TinyDB as current workflow
    current_workflow_table.truncate()
    current_workflow_table.insert(test_flowchart)

    # Also save to workflows table
    Workflow = Query()
    workflows_table.upsert(test_flowchart, Workflow.id == "current_flowchart")

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
        # Clean up the test data after the test
        current_workflow_table.truncate()

        workflows_table.remove(Workflow.id == "current_flowchart")


def test_extract_workflow_metadata(mock_workflow_with_metadata):
    """Test extracting metadata from a workflow"""
    # Extract metadata from the workflow
    workflow_id = mock_workflow_with_metadata
    metadata = extract_workflow_metadata(workflow_id)

    # Check that the metadata was extracted correctly
    assert metadata["name"] == "Custom Workflow Name"
    assert metadata["description"] == "Custom workflow description"


def test_list_workflows_with_custom_names(mock_workflow_with_metadata):
    """Test listing workflows with custom names from TinyDB"""
    # Send a request to the list_workflows endpoint
    response = client.get("/workflows")

    # Check the response
    assert response.status_code == 200
    workflows = response.json()

    # Find the test workflow in the list
    test_workflow = next((w for w in workflows if w["id"] == mock_workflow_with_metadata), None)

    # Check that the workflow was found and has the correct name
    assert test_workflow is not None
    assert test_workflow["name"] == "Custom Workflow Name"
    assert test_workflow["default_name"] == "test_workflow_with_metadata"


def test_update_workflow_name(mock_workflow, mock_workflow_id):
    """Test updating a workflow name"""
    # Define the new name
    new_name = "Updated Workflow Name"

    # Send a request to update the workflow name
    response = client.put(f"/workflows/{mock_workflow_id}/name", json={"name": new_name})

    # Print response details if it fails
    if response.status_code != 200:
        print(f"\nDEBUG: Response status: {response.status_code}, Response body: {response.json()}")
    # Check the response
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Get the workflow from TinyDB
    db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
    db = TinyDB(db_path)
    workflows_table = db.table("workflows")
    Workflow = Query()
    workflow_data = workflows_table.get(Workflow.id == "test_workflow")
    # Check that the name was updated in the database
    assert "metadata" in workflow_data
    assert workflow_data["metadata"]["name"] == new_name

    # Send a request to the list_workflows endpoint
    response = client.get("/workflows")

    # Check that the updated name is returned in the list
    workflows = response.json()
    test_workflow = next((w for w in workflows if w["id"] == mock_workflow_id), None)
    assert test_workflow is not None
    assert test_workflow["name"] == new_name


if __name__ == "__main__":
    pytest.main(["-xvs", "test_api_server.py"])
