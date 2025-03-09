"""Tests for workflow execution with multiple nodes"""

import json
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from api_server import api, WorkflowExecuteRequest


# Create a test client
client = TestClient(api)


@pytest.fixture
def mock_multi_node_workflow():
    """Create a mock workflow file with multiple connected nodes for testing"""
    # Define the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    test_workflow_path = os.path.join(workflows_dir, "test_multi_node_workflow.yaml")

    # Create a test workflow with multiple nodes and connections
    test_workflow = {
        "metadata": {"name": "Multi-Node Test Workflow"},
        "nodes": [
            {"id": "node-1", "type": "act", "position": {"x": 100, "y": 100}, "prompt": "Who's the queen?"},
            {
                "id": "node-2",
                "type": "act",
                "position": {"x": 300, "y": 300},
                "prompt": "Write me a one paragraph summary of her life",
            },
        ],
        "connections": [
            {"from": {"nodeId": "node-1", "position": "bottom"}, "to": {"nodeId": "node-2", "position": "top"}}
        ],
    }

    # Write the test workflow to a file
    with open(test_workflow_path, "w", encoding="utf-8") as f:
        yaml.dump(test_workflow, f)

    yield "test_multi_node_workflow.yaml"

    # Clean up the test file after the test
    if os.path.exists(test_workflow_path):
        os.remove(test_workflow_path)


@pytest.fixture
def mock_multi_node_flowchart():
    """Create a mock current flowchart file with multiple connected nodes for testing"""
    # Define the path to the test flowchart file
    flowcharts_dir = os.path.join(os.path.dirname(__file__), "flowcharts")
    os.makedirs(flowcharts_dir, exist_ok=True)
    test_flowchart_path = os.path.join(flowcharts_dir, "current_flowchart.yaml")

    # Create a test flowchart with multiple nodes and connections
    test_flowchart = {
        "metadata": {"name": "Multi-Node Test Flowchart"},
        "nodes": [
            {"id": "node-1", "type": "act", "position": {"x": 100, "y": 100}, "prompt": "Who's the queen?"},
            {
                "id": "node-2",
                "type": "act",
                "position": {"x": 300, "y": 300},
                "prompt": "Write me a one paragraph summary of her life",
            },
        ],
        "connections": [
            {"from": {"nodeId": "node-1", "position": "bottom"}, "to": {"nodeId": "node-2", "position": "top"}}
        ],
    }

    # Write the test flowchart to a file
    with open(test_flowchart_path, "w", encoding="utf-8") as f:
        yaml.dump(test_flowchart, f)

    yield

    # Clean up the test file after the test
    if os.path.exists(test_flowchart_path):
        os.remove(test_flowchart_path)


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_workflow_traverses_nodes(mock_agent_class, mock_multi_node_workflow):
    """Test that execute_workflow traverses all nodes in the workflow"""
    # Create a mock agent instance with different responses for each call
    mock_agent = MagicMock()

    # Set up the mock to return different values for each call
    mock_agent.run = AsyncMock()
    mock_agent.run.side_effect = [
        # First node result - this is passed to the second node
        {
            "final_result": "Queen Elizabeth II",
            "goal_assessment_result": None,
            "goal_assessment_feedback": None,
            "error": None,
        },
        # Second node result - this becomes the final result
        {
            "final_result": "Queen Elizabeth II was the longest-reigning British monarch, serving from 1952 until her death in 2022.",
            "goal_assessment_result": None,
            "goal_assessment_feedback": None,
            "error": None,
        },
    ]

    mock_agent_class.return_value = mock_agent

    # Create a test request
    request_data = {"input": "Test input"}

    # Send a request to the endpoint
    response = client.post(f"/workflows/{mock_multi_node_workflow}/execute", json=request_data)

    # Check the response
    assert response.status_code == 200

    # The response is JSON-encoded, so we need to parse it
    response_json = response.json()
    final_result = response_json["final_result"]

    # The final result might be a JSON string that needs to be parsed
    try:
        parsed_result = json.loads(final_result)
        if isinstance(parsed_result, dict) and "response_text" in parsed_result:
            final_text = parsed_result["response_text"]
            assert final_text is not None
            assert "Queen Elizabeth II was the longest-reigning British monarch" in final_text
        else:
            assert "Queen Elizabeth II was the longest-reigning British monarch" in final_result
    except json.JSONDecodeError:
        # If it's not JSON, check the raw string
        assert "Queen Elizabeth II was the longest-reigning British monarch" in final_result

    # Verify that the agent was called twice with the correct parameters
    assert mock_agent.run.call_count == 2

    # First call should be with the first node's prompt and the initial input
    first_call_args = mock_agent.run.call_args_list[0][0]
    assert "Who's the queen?" in first_call_args[0]
    assert "Test input" in first_call_args[0]

    # Second call should be with the second node's prompt and the result from the first node
    second_call_args = mock_agent.run.call_args_list[1][0]
    assert "Write me a one paragraph summary of her life" in second_call_args[0]
    assert "Queen Elizabeth II" in second_call_args[0]


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_execute_current_flowchart_traverses_nodes(mock_agent_class, mock_multi_node_flowchart):
    """Test that execute_current_flowchart traverses all nodes in the flowchart"""
    # Create a mock agent instance with different responses for each call
    mock_agent = MagicMock()

    # Set up the mock to return different values for each call
    mock_agent.run = AsyncMock()
    mock_agent.run.side_effect = [
        # First node result - this is passed to the second node
        {
            "final_result": "Queen Elizabeth II",
            "goal_assessment_result": None,
            "goal_assessment_feedback": None,
            "error": None,
        },
        # Second node result - this becomes the final result
        {
            "final_result": "Queen Elizabeth II was the longest-reigning British monarch, serving from 1952 until her death in 2022.",
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

    # The response is JSON-encoded, so we need to parse it
    response_json = response.json()
    final_result = response_json["final_result"]

    # The final result might be a JSON string that needs to be parsed
    try:
        parsed_result = json.loads(final_result)
        if isinstance(parsed_result, dict) and "response_text" in parsed_result:
            final_text = parsed_result["response_text"]
            assert final_text is not None
            assert "Queen Elizabeth II was the longest-reigning British monarch" in final_text
        else:
            assert "Queen Elizabeth II was the longest-reigning British monarch" in final_result
    except json.JSONDecodeError:
        # If it's not JSON, check the raw string
        assert "Queen Elizabeth II was the longest-reigning British monarch" in final_result

    # Verify that the agent was called twice with the correct parameters
    assert mock_agent.run.call_count == 2

    # First call should be with the first node's prompt and the initial input
    first_call_args = mock_agent.run.call_args_list[0][0]
    assert "Who's the queen?" in first_call_args[0]
    assert "Test input" in first_call_args[0]

    # Second call should be with the second node's prompt and the result from the first node
    second_call_args = mock_agent.run.call_args_list[1][0]
    assert "Write me a one paragraph summary of her life" in second_call_args[0]
    assert "Queen Elizabeth II" in second_call_args[0]


@pytest.mark.asyncio
@patch("api_server.PlanAndExecuteAgent")
async def test_workflow_with_no_connections(mock_agent_class):
    """Test executing a workflow with no connections between nodes"""
    # Define the path to the test workflow file
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    test_workflow_path = os.path.join(workflows_dir, "test_no_connections.yaml")

    # Create a test workflow with multiple nodes but no connections
    test_workflow = {
        "metadata": {"name": "No Connections Test Workflow"},
        "nodes": [
            {"id": "node-1", "type": "act", "position": {"x": 100, "y": 100}, "prompt": "First node prompt"},
            {"id": "node-2", "type": "act", "position": {"x": 300, "y": 300}, "prompt": "Second node prompt"},
        ],
        "connections": [],  # No connections
    }

    # Write the test workflow to a file
    with open(test_workflow_path, "w", encoding="utf-8") as f:
        yaml.dump(test_workflow, f)

    try:
        # Create a mock agent instance
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            return_value={
                "final_result": "Test result",
                "goal_assessment_result": None,
                "goal_assessment_feedback": None,
                "error": None,
            }
        )
        mock_agent_class.return_value = mock_agent

        # Create a test request
        request_data = {"input": "Test input"}

        # Send a request to the endpoint
        response = client.post("/workflows/test_no_connections.yaml/execute", json=request_data)

        # Check the response
        assert response.status_code == 200

        # Verify that the agent was called only once with the first node's prompt
        # since there are no connections to follow
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args[0][0]
        assert "First node prompt" in call_args

    finally:
        # Clean up the test file after the test
        if os.path.exists(test_workflow_path):
            os.remove(test_workflow_path)


if __name__ == "__main__":
    pytest.main(["-xvs", "test_workflow_execution.py"])
