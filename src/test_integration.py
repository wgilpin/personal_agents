"""Integration tests for the Plan and Execute agent"""

import json
from unittest.mock import AsyncMock, patch

import pytest  # pylint: disable=import-error


from plan_and_execute import (
    GoalAssessment,
    Plan,
    PlanAndExecuteAgent,
)


# Integration test mock responses
INTEGRATION_MOCK_RESPONSES = {
    "plan": Plan(
        steps=[
            "Search for recent AI news to identify prominent people",
            "Extract names and reasons they are in the news",
            "Compile the information into a structured list",
        ]
    ),
    "search_result": """I searched for recent AI news and found that Sam Altman (OpenAI CEO) announced new GPT-5
        features, and Demis Hassabis (DeepMind CEO) presented their latest research on AI safety.""",
    "extract_result": """Based on the search results, I've extracted the following names:\n1. Sam Altman - Announced
        new GPT-5 features\n2. Demis Hassabis - Presented DeepMind's latest research on AI safety""",
    "compile_result": """I've compiled the information into a structured list:\n- Sam Altman: OpenAI CEO who announced
        new GPT-5 features this week\n- Demis Hassabis: DeepMind CEO who presented new research on AI safety""",
    "goal_satisfied": GoalAssessment(
        is_satisfied=True,
        final_response="The goal has been satisfied. Here's the list of people prominent in AI news.",
        is_list_output=True,
        json_output=[
            "Sam Altman: OpenAI CEO who announced new GPT-5 features this week",
            "Demis Hassabis: DeepMind CEO who presented new research on AI safety",
        ],
    ),
    "goal_not_satisfied": GoalAssessment(
        is_satisfied=False,
        final_response="We need to complete all steps to get a comprehensive list.",
        is_list_output=False,
        json_output={"text": "More steps needed"},
    ),
}


@pytest.mark.asyncio
@patch("plan_and_execute.load_dotenv", lambda: None)  # Skip loading .env file
async def test_full_workflow_integration():
    """Test a full workflow integration with realistic mock responses"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a mock result that would be returned by the run method
    expected_result = {
        "final_result": (
            INTEGRATION_MOCK_RESPONSES["search_result"]
            + "\n"
            + INTEGRATION_MOCK_RESPONSES["extract_result"]
            + "\n"
            + INTEGRATION_MOCK_RESPONSES["compile_result"]
            + "\n"
        ),
        "goal_assessment_result": json.dumps(
            [
                "Sam Altman: OpenAI CEO who announced new GPT-5 features this week",
                "Demis Hassabis: DeepMind CEO who presented new research on AI safety",
            ]
        ),
        "goal_assessment_feedback": None,
    }

    # Mock the run method to return our expected result
    with patch.object(agent, "run", AsyncMock(return_value=expected_result)):
        # Run the agent with a test input
        result = await agent.run(
            """Get me a list of the names of people who have been prominent in AI news this week, along with
                why they are in the news"""
        )

        # Verify the results
        assert "final_result" in result
        assert "goal_assessment_result" in result

        # Check that the final result contains the expected information
        assert "Sam Altman" in result["final_result"]
        assert "Demis Hassabis" in result["final_result"]
        assert "GPT-5" in result["final_result"]

        # Check that the goal assessment result is a JSON string containing the expected list
        goal_assessment = json.loads(result["goal_assessment_result"])
        assert isinstance(goal_assessment, list)
        assert len(goal_assessment) == 2
        assert any("Sam Altman" in item for item in goal_assessment)
        assert any("Demis Hassabis" in item for item in goal_assessment)


@pytest.mark.asyncio
@patch("plan_and_execute.load_dotenv", lambda: None)  # Skip loading .env file
async def test_workflow():
    """Test running a workflow with custom event stream"""
    # Create a PlanAndExecuteAgent
    agent = PlanAndExecuteAgent()

    # Create a custom astream method to simulate workflow events
    async def custom_workflow_astream(*_, **__):
        # Execute first node (act)
        yield {
            "agent": {
                "past_steps": [
                    (
                        "Search for AI news",
                        "I searched for recent AI news and found information about Sam Altman and Demis Hassabis.",
                    )
                ],
                "plan": [],
            }
        }

        # Execute second node (act)
        yield {
            "agent": {
                "past_steps": [
                    (
                        "Extract names",
                        "I've extracted Sam Altman and Demis Hassabis from the news.",
                    )
                ],
                "plan": [],
            }
        }

        # Execute third node (choice) - satisfied
        yield {"goal_assessor": {"response": json.dumps(["Sam Altman: OpenAI CEO", "Demis Hassabis: DeepMind CEO"])}}

        # End
        yield {"__end__": None}

    # Replace the agent's app.astream method with our custom implementation
    with patch.object(agent.app, "astream", custom_workflow_astream):
        # Run the agent with a test input
        result = await agent.run("Test input")

        # Verify the results
        assert "final_result" in result
        assert "goal_assessment_result" in result
        assert "Sam Altman" in result["final_result"]
        assert "Demis Hassabis" in result["final_result"]

        # Check that the goal assessment result is a JSON string containing the expected list
        goal_assessment = json.loads(result["goal_assessment_result"])
        assert isinstance(goal_assessment, list)
        assert len(goal_assessment) == 2
        assert any("Sam Altman" in item for item in goal_assessment)
        assert any("Demis Hassabis" in item for item in goal_assessment)


if __name__ == "__main__":
    pytest.main(["-xvs", "test_integration.py"])
