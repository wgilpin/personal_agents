"""Tests for the API server"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api_server import api, WorkflowExecuteRequest


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
        json.dump(test_workflow, f)

    yield "test_workflow.yaml"

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


if __name__ == "__main__":
    pytest.main(["-xvs", "test_api_server.py"])
