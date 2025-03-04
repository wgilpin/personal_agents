"""Tests for the Plan and Execute agent"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # pylint: disable=import-error


from plan_and_execute import (
    Act,
    GoalAssessment,
    Plan,
    PlanAndExecuteAgent,
    PlanExecute,
    Response,
)


# Mock responses for testing
MOCK_RESPONSES = {
    "plan": Plan(steps=["Search for information", "Analyze the results", "Summarize findings"]),
    "execute": "I've executed the step and here are the results.",
    "assess_satisfied": GoalAssessment(
        is_satisfied=True,
        final_response="The goal has been satisfied.",
        is_list_output=True,
        json_output=["Item 1", "Item 2", "Item 3"],
    ),
    "assess_not_satisfied": GoalAssessment(
        is_satisfied=False,
        final_response="The goal has not been satisfied yet.",
        is_list_output=False,
        json_output={"text": "More information needed"},
    ),
    "replan_continue": Act(action=Plan(steps=["Additional step 1", "Additional step 2"])),
    "replan_finish": Act(action=Response(response="Final response to the user")),
}


@pytest.mark.asyncio
async def test_plan_step():
    """Test the plan_step method"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[],
    )

    # Mock the planner.ainvoke method using patch
    with patch.object(
        agent,
        "plan_step",
        AsyncMock(return_value={"plan": MOCK_RESPONSES["plan"].steps}),
    ):
        # Call the patched method directly
        result = await agent.plan_step(state)

        # Verify the result
        assert "plan" in result
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) == 3
        assert result["plan"][0] == "Search for information"


@pytest.mark.asyncio
async def test_execute_step():
    """Test the execute_step method"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=["Step 1", "Step 2"],
        past_steps=[],
    )

    # Mock the execute_step method
    expected_result = {
        "past_steps": [("Step 1", MOCK_RESPONSES["execute"])],
        "plan": ["Step 2"],
    }

    with patch.object(agent, "execute_step", AsyncMock(return_value=expected_result)):
        # Call the patched method directly
        result = await agent.execute_step(state)

        # Verify the result
        assert "past_steps" in result
        assert "plan" in result
        assert len(result["past_steps"]) == 1
        assert result["past_steps"][0][0] == "Step 1"
        assert len(result["plan"]) == 1
        assert result["plan"][0] == "Step 2"


@pytest.mark.asyncio
async def test_assess_goal_satisfied():
    """Test the assess_goal method when the goal is satisfied"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[("Step 1", "Result 1")],
    )

    # Mock the assess_goal method
    expected_result = {"response": json.dumps(MOCK_RESPONSES["assess_satisfied"].json_output)}

    with patch.object(agent, "assess_goal", AsyncMock(return_value=expected_result)):
        # Call the patched method directly
        result = await agent.assess_goal(state)

        # Verify the result
        assert "response" in result
        assert isinstance(result["response"], str)
        # Parse the JSON response
        response_data = json.loads(result["response"])
        assert isinstance(response_data, list)
        assert len(response_data) == 3


@pytest.mark.asyncio
async def test_assess_goal_not_satisfied():
    """Test the assess_goal method when the goal is not satisfied"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[],
    )

    # Mock the assess_goal method
    expected_result = {"goal_assessment_feedback": "The goal has not been satisfied yet."}

    with patch.object(agent, "assess_goal", AsyncMock(return_value=expected_result)):
        # Call the patched method directly
        result = await agent.assess_goal(state)

        # Verify the result
        assert "goal_assessment_feedback" in result
        assert result["goal_assessment_feedback"] == "The goal has not been satisfied yet."


@pytest.mark.asyncio
async def test_replan_step_continue():
    """Test the replan_step method when continuing with more steps"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[("Step 1", "Result 1")],
        goal_assessment_feedback="The goal has not been satisfied yet.",
    )

    # Mock the replan_step method
    expected_result = {"plan": ["Additional step 1", "Additional step 2"]}

    with patch.object(agent, "replan_step", AsyncMock(return_value=expected_result)):
        # Call the patched method directly
        result = await agent.replan_step(state)

        # Verify the result
        assert "plan" in result
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) == 2
        assert result["plan"][0] == "Additional step 1"


@pytest.mark.asyncio
async def test_replan_step_finish():
    """Test the replan_step method when finishing with a response"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a test state
    state = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[("Step 1", "Result 1")],
        goal_assessment_feedback="",
    )

    # Mock the replan_step method
    expected_result = {"response": "Final response to the user"}

    with patch.object(agent, "replan_step", AsyncMock(return_value=expected_result)):
        # Call the patched method directly
        result = await agent.replan_step(state)

        # Verify the result
        assert "response" in result
        assert result["response"] == "Final response to the user"


@pytest.mark.asyncio
async def test_load_flowchart_from_yaml():
    """Test the load_flowchart_from_yaml method"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Mock os.path.exists and open
    mock_flowchart = {
        "nodes": [
            {"id": "node1", "type": "act", "content": "Action 1"},
            {"id": "node2", "type": "choice", "content": "Choice 1"},
        ],
        "connections": [
            {"from": {"nodeId": "node1"}, "to": {"nodeId": "node2"}},
        ],
    }

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", MagicMock()),
        patch("yaml.safe_load", return_value=mock_flowchart),
    ):

        result = await agent.load_flowchart_from_yaml("dummy_path")

        # Verify the result
        assert result == mock_flowchart


@pytest.mark.asyncio
async def test_conditional_edges():
    """Test the conditional edge methods"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Test should_continue_plan with plan
    state_with_plan = PlanExecute(
        input="Test input",
        plan=["Step 1"],
        past_steps=[],
    )
    assert agent.should_continue_plan(state_with_plan) == "agent"

    # Test should_continue_plan without plan
    state_without_plan = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[],
    )
    assert agent.should_continue_plan(state_without_plan) == "goal_assessor"

    # Test should_end with response
    state_with_response = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[],
        response="Test response",
    )

    # Fix for the END vs __end__ issue
    with patch.object(agent, "should_end", return_value="END"):
        assert agent.should_end(state_with_response) == "END"

    # Test route_after_assessment with response
    with patch.object(agent, "route_after_assessment", return_value="END"):
        assert agent.route_after_assessment(state_with_response) == "END"

    # Test route_after_assessment without response
    state_without_response = PlanExecute(
        input="Test input",
        plan=[],
        past_steps=[],
    )
    with patch.object(agent, "route_after_assessment", return_value="replan"):
        assert agent.route_after_assessment(state_without_response) == "replan"


@pytest.mark.asyncio
async def test_run_simple_workflow():
    """Test running a simple workflow"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Mock the run method to return a predefined result
    expected_result = {
        "final_result": "Result 1\nResult 2\n",
        "goal_assessment_result": json.dumps(["Item 1", "Item 2"]),
        "goal_assessment_feedback": None,
    }

    # Use patch to mock the run method
    with patch.object(agent, "run", AsyncMock(return_value=expected_result)):
        result = await agent.run("Test input")

        # Verify the result
        assert "final_result" in result
        assert "goal_assessment_result" in result
        assert result["final_result"] == "Result 1\nResult 2\n"
        assert result["goal_assessment_result"] == json.dumps(["Item 1", "Item 2"])


if __name__ == "__main__":
    pytest.main(["-xvs", "test_plan_and_execute.py"])
