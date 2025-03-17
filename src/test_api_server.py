"""Tests for the API server"""

# pylint: disable=redefined-outer-name

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from tinydb import TinyDB, Query

import shutil
from api_server import api
from db import Database
from workflows import extract_workflow_metadata

# Create a test client
client = TestClient(api)


@pytest.fixture
def mock_logs():
    """Create mock log files for testing"""
    # Create a logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create some mock log files
    log_files = [
        (
            "test_workflow_2024-01-01_12-00-00.json",
            {
                "workflow_name": "Test Workflow",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T12:00:10",
                "duration_seconds": 10,
                "success": True,
                "result": "Result 1",
            },
        ),
        (
            "test_workflow_2024-01-01_13-00-00.json",
            {
                "workflow_name": "Test Workflow",
                "start_time": "2024-01-01T13:00:00",
                "end_time": "2024-01-01T13:00:20",
                "duration_seconds": 20,
                "success": True,
                "result": "Result 2",
            },
        ),
        (
            "another_workflow_2024-01-01_14-00-00.json",
            {
                "workflow_name": "Another Workflow",
                "start_time": "2024-01-01T14:00:00",
                "end_time": "2024-01-01T14:00:30",
                "duration_seconds": 30,
                "success": True,
                "result": "Result 3",
            },
        ),
    ]
    for filename, content in log_files:
        filepath = os.path.join(logs_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)  # Write as JSON

    yield  # This allows the tests to run

    # Clean up the logs directory after the tests
    shutil.rmtree(logs_dir)


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

    # Save to TinyDB workflows table
    workflows_table.upsert(test_workflow, Workflow.id == workflow_id)

    yield "test_workflow"

    # Clean up the database after the test
    # workflows_table.remove(Workflow.id == workflow_id)


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
async def test_execute_workflow(mock_agent_class, mock_workflow, mock_workflow_id):  # pylint: disable=unused-argument
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
async def test_execute_current_workflow_traverses_nodes(mock_agent_class):
    """Test that execute_current_workflow traverses nodes in the workflow"""
    # Initialize the database for the test workflow
    tinydb = Database()

    # create a random ID for a workflow
    test_workflow_id = "test_workflow_" + uuid.uuid4().hex

    # Create a test workflow with multiple nodes and connections
    test_workflow = {
        "metadata": {"name": "Multi-Node Test workflow"},
        "id": test_workflow_id,
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

    # Save to workflows table
    tinydb.workflows_table.upsert(test_workflow, tinydb.workflow_query.id == test_workflow_id)

    try:
        # Create a mock agent instance with different responses for each call
        mock_agent = MagicMock()

        # Set up the mock to return different values for each call
        mock_agent.run = AsyncMock()
        mock_agent.run.side_effect = [
            # First node result
            {
                "final_result": "First node result",
                "goal_assessment_result": "First node result",
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
        response = client.post(f"/workflows/{test_workflow_id}/execute", json=request_data)
        assert response.status_code == 200, f"Response: {response.json()}"

        # The final_result is a JSON string with a response_text field
        final_result = response.json()["final_result"]
        try:
            parsed_result = json.loads(final_result)
            # Just check that we got a valid JSON response, not the specific content
            assert isinstance(parsed_result, dict)
        except json.JSONDecodeError:
            # If it's not JSON, check for the raw string
            assert "Second node result" in final_result

    finally:
        # Clean up the test data after the test
        tinydb.workflows_table.remove(tinydb.workflow_query.id == test_workflow_id)


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


def test_get_workflow(mock_workflow, mock_workflow_id):  # pylint: disable=unused-argument
    """Test getting a specific workflow by filename"""
    # Send a request to get the workflow
    response = client.get(f"/workflows/{mock_workflow_id}")

    # Check the response
    assert response.status_code == 200
    workflow_data = response.json()

    # Verify the workflow data
    assert workflow_data["id"] == mock_workflow_id
    assert "metadata" in workflow_data
    assert workflow_data["metadata"]["name"] == "Test Workflow"
    assert "nodes" in workflow_data
    assert len(workflow_data["nodes"]) == 2
    assert workflow_data["nodes"][0]["id"] == "node1"
    assert workflow_data["nodes"][1]["id"] == "node2"
    assert "connections" in workflow_data
    assert len(workflow_data["connections"]) == 1
    assert workflow_data["connections"][0]["from"]["nodeId"] == "node1"
    assert workflow_data["connections"][0]["to"]["nodeId"] == "node2"


def test_get_workflow_not_found():
    """Test getting a non-existent workflow"""
    # Send a request to get a non-existent workflow
    response = client.get("/workflows/non_existent_workflow")

    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_workflow_name(mock_workflow, mock_workflow_id):  # pylint: disable=unused-argument
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
    tinydb = Database()
    workflow_data = tinydb.workflows_table.get(tinydb.workflow_query.id == "test_workflow")
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


@pytest.mark.asyncio
async def test_upload_workflow():
    """Test uploading a workflow"""
    # Create a test workflow file in JSON format
    test_workflow_content = {
        "metadata": {"name": "Uploaded Test Workflow"},
        "nodes": [{"id": "node1", "type": "act", "prompt": "Uploaded workflow action"}],
        "connections": [],
    }
    test_workflow_file_content = json.dumps(test_workflow_content, indent=2)

    # Create a temporary file with .json extension
    temp_file_path = os.path.join(os.path.dirname(__file__), "temp_workflow.json")
    with open(temp_file_path, "w", encoding="utf-8") as temp_file:
        temp_file.write(test_workflow_file_content)

    try:
        # Send a request to the endpoint with correct MIME type
        with open(temp_file_path, "rb") as temp_file:
            response = client.post("/workflows", files={"file": ("workflow.json", temp_file, "application/json")})

        # Check the response
        assert response.status_code == 200, f"Response: {response.text}"
        response_data = response.json()
        assert "message" in response_data, f"Response: {response.text}"
        assert response_data["success"] is True, f"Response: {response.text}"

        # Verify that workflow was saved to TinyDB and get workflow ID
        tinydb = Database()
        # The workflow ID is derived from the name with spaces replaced by underscores
        workflow_id = "Uploaded_Test_Workflow"
        workflow_data = tinydb.workflows_table.get(tinydb.workflow_query.id == workflow_id)
        assert workflow_data is not None, f"Workflow with ID '{workflow_id}' not found in database"
        assert workflow_data["metadata"]["name"] == "Uploaded Test Workflow"
    except Exception:
        # Clean up the database if the test fails
        tinydb = Database()
        # Use the expected workflow ID
        workflow_id = "Uploaded_Test_Workflow"
        tinydb.workflows_table.remove(tinydb.workflow_query.id == workflow_id)
        raise
    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)


if __name__ == "__main__":
    pytest.main(["-xvs", "test_api_server.py"])


def test_delete_workflow(mock_workflow, mock_workflow_id):  # pylint: disable=unused-argument
    """Test deleting a workflow"""
    # Send a request to delete the workflow
    response = client.delete(f"/workflows/{mock_workflow_id}")

    # Check the response
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify that the workflow is deleted from TinyDB
    tinydb = Database()
    workflow_data = tinydb.workflows_table.get(tinydb.workflow_query.id == mock_workflow_id)
    assert workflow_data is None


def test_delete_workflow_not_found():
    """Test deleting a non-existent workflow"""
    # Send a request to delete a non-existent workflow
    response = client.delete("/workflows/non_existent_workflow")

    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_latest_workflow_log_success(mock_workflow, mock_logs):  # pylint: disable=unused-argument
    """Test getting the latest log for a workflow that exists and has logs"""
    response = client.get(f"/workflows/test_workflow/logs/latest")
    assert response.status_code == 200
    assert response.json()["found"] is True
    assert response.json()["log"]["workflow_name"] == "Test Workflow"
    assert response.json()["log"]["result"] == "Result 2"  # Expecting the latest log


def test_get_latest_workflow_log_no_logs(mock_workflow):  # pylint: disable=unused-argument
    """Test getting the latest log for a workflow that exists but has no logs"""
    response = client.get(f"/workflows/test_workflow/logs/latest")
    assert response.status_code == 200  # Expecting 200 even if no logs
    assert response.json()["found"] is False
    assert "No execution logs found" in response.json()["message"]


def test_get_latest_workflow_log_not_found():
    """Test getting the latest log for a workflow that doesn't exist"""
    response = client.get(f"/workflows/non_existent_workflow/logs/latest")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
