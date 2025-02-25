# -*- coding: utf-8 -*-
"""plan-and-execute.ipynb"""

# Original file is located at
#     https://colab.research.google.com/github/langchain-ai/langgraph/blob/main/docs/docs/tutorials/plan-and-execute/plan-and-execute.ipynb

# # Plan-and-Execute
# %%
## Setup
import asyncio
import argparse
import io
import json
import operator
import os
import sys
from typing import Annotated, List, Tuple, Union, Dict, Any

from dotenv import load_dotenv
from IPython.display import Image, display
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI  # pylint: disable=import-error
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from PIL import Image as PILImage  # pylint: disable=import-error
from pydantic import BaseModel, Field
from tavily import TavilyClient  # pylint: disable=import-error
from typing_extensions import TypedDict

MODEL_NAME = "gpt-4o"

load_dotenv()


## Define Tools
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@tool
def search(query: str):
    """Call to surf the web using Tavily."""
    return tavily_client.search(query)


tools = [search]

## Define our Execution Agent
memory = MemorySaver()

# Choose the LLM that will drive the agent
llm = ChatOpenAI(model=MODEL_NAME)
prompt = "You are a helpful assistant."
agent_executor = create_react_agent(llm, tools, prompt=prompt)

## Define the State
# First, we will need to track the current plan as a list of strings.
# Next, we should track previously executed steps as a list of tuples
# (these tuples will contain the step and then the result)
# Finally, state to represent the final response as well as the original input.


class PlanExecute(TypedDict):
    """PlanExecute is used to track the current state of the agent"""

    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str


## Planning Step
# Use function calling to create a plan.


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )


planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """For the given objective, come up with a simple step by step plan.
            This plan should involve individual tasks, that if executed correctly will yield the correct answer.
            The plan should use trhe supplied tools when appropriate. The tools are """
            + ", ".join([f"{tool.name}: {tool.description}" for tool in tools])
            + """Do not add any superfluous steps.
            The result of the final step should be the final answer.
            Make sure that each step has all the information needed - do not skip steps.""",
        ),
        ("placeholder", "{messages}"),
    ]
)
planner = planner_prompt | ChatOpenAI(
    model=MODEL_NAME, temperature=0
).with_structured_output(Plan)

## Re-Plan Step
# create a step that re-does the plan based on the result of the previous step.


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )


replanner_prompt = ChatPromptTemplate.from_template(
    """
    For the given objective, come up with a simple step by step plan.
    This plan should involve individual tasks, that if executed correctly
    will yield the correct answer. Do not add any superfluous steps.
    The result of the final step should be the final answer.
    Make sure that each step has all the information needed - do not skip steps.

    Your objective was this:
    {input}

    Your original plan was this:
    {plan}

    You have currently done the follow steps:
    {past_steps}

    Update your plan accordingly.
    If no more steps are needed and you can return to the user, then respond with that.
    Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done.
    Do not return previously done steps as part of the plan, and do not add any steps that
    are effectively the same as steps that have already been done.
    """
)


replanner = replanner_prompt | ChatOpenAI(
    model=MODEL_NAME, temperature=0
).with_structured_output(Act)


async def execute_step(state: PlanExecute):
    """Execute the first step in the plan and update the state"""
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""
        For the following plan:
        {plan_str}\n\nYou are tasked with executing step {1}, {task}."""
    agent_response = await agent_executor.ainvoke(
        {"messages": [("user", task_formatted)]}
    )
    # Remove the executed step from the plan
    remaining_plan = plan[1:] if len(plan) > 1 else []
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
        "plan": remaining_plan,
    }


async def plan_step(state: PlanExecute):
    """Generate a new plan based on the current input"""
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}


async def replan_step(state: PlanExecute):
    """Replan based on the current state"""
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        print(f"Response : {output.action.response}")
        return {"response": output.action.response}
    else:
        print("REPLAN")
        for task in output.action.steps:
            print(f"- {task}")
        return {"plan": output.action.steps}


# Create a very simple prompt template with only the variables we know we have
goal_assessor_system_template = """
You are a goal assessment expert. Your job is to determine if the user's original goal has been satisfied 
based on the work that has been done so far.

IMPORTANT: Analyze if the goal is asking for a list or text:
- If the goal is asking for a list (e.g., "list of people", "list of items", etc.), format your output as a JSON list.
- If the goal is asking for text (e.g., explanation, description, etc.), format your output as a JSON object with one entry.

For example, if the goal was "Get me a list of AI researchers", your json_output should be a list like:
["Geoffrey Hinton", "Yann LeCun", "Yoshua Bengio"]

If the goal was "Explain what AI is", your json_output should be a json object with a single key & value. The key is  "response_text", the value is your answer as a text string.
"""

goal_assessor_user_template = """
Original goal: {input}

Original plan: {plan}

Steps completed: {past_steps}

Based on the above information, has the original goal been fully satisfied? 
If yes, provide a final response to the user that addresses their original goal.
If no, explain why the goal hasn't been satisfied yet and what still needs to be done.
"""

# Create a simple ChatPromptTemplate with separate system and user messages
goal_assessor_prompt = ChatPromptTemplate.from_messages(
    [("system", goal_assessor_system_template), ("human", goal_assessor_user_template)]
)


class GoalAssessment(BaseModel):
    """Assessment of whether the goal has been satisfied"""

    is_satisfied: bool = Field(description="Whether the goal has been satisfied")
    final_response: str = Field(
        description="Final response to the user if goal is satisfied, or explanation of what's missing if not"
    )
    is_list_output: bool = Field(
        description="Whether the output should be a list (true) or a text object (false)"
    )
    json_output: Union[List[str], Dict[str, str]] = Field(
        description="The JSON output, either a list of strings or an object with one entry"
    )


goal_assessor = goal_assessor_prompt | ChatOpenAI(
    model=MODEL_NAME, temperature=0
).with_structured_output(GoalAssessment, method="function_calling")


async def assess_goal(state: PlanExecute):
    """Assess if the goal has been satisfied based on the completed steps"""
    print("Assess Goal:")
    # Create a string representation of the plan for the prompt
    plan_str = "\n".join(
        f"{i+1}. {step}" for i, step in enumerate(state.get("plan", []))
    )

    # Create a string representation of past steps
    past_steps_str = ""
    for step, result in state.get("past_steps", []):
        past_steps_str += f"Step: {step}\nResult: {result}\n\n"

    assessment = await goal_assessor.ainvoke(
        {"input": state["input"], "plan": plan_str, "past_steps": past_steps_str}
    )

    if assessment.is_satisfied:
        print("Satisfied!")
        # Format the response as JSON based on whether it should be a list or text object
        if assessment.is_list_output:
            # Ensure we have a JSON list
            json_output = (
                assessment.json_output
                if isinstance(assessment.json_output, list)
                else []
            )
            print(f"JSON LIST OUTPUT: {json.dumps(json_output)}")
        else:
            # Ensure we have a JSON object with one entry
            json_output = (
                assessment.json_output
                if isinstance(assessment.json_output, dict)
                else {"text": assessment.final_response}
            )
            print(f"JSON OBJECT OUTPUT: {json.dumps(json_output)}")

        # Return the JSON string as the response
        return {"response": json.dumps(assessment.json_output)}
    else:
        print(f"GOAL NOT SATISFIED: {assessment.final_response}")
        return {}


def should_continue_plan(state: PlanExecute):
    """Check if there are more steps in the plan to execute"""
    if state["plan"]:
        return "agent"
    else:
        return "goal_assessor"


def should_end(state: PlanExecute):
    """Check if the workflow should end"""
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


def route_after_assessment(state: PlanExecute):
    """Determine next step after goal assessment"""
    if "response" in state and state["response"]:
        return END
    else:
        return "replan"


workflow = StateGraph(PlanExecute)

# Add the plan node
workflow.add_node("planner", plan_step)

# Add the execution step
workflow.add_node("agent", execute_step)

# Add the goal assessment node
workflow.add_node("goal_assessor", assess_goal)

# Add a replan node
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")

# From plan we go to agent
workflow.add_edge("planner", "agent")

# From agent, we check if there are more steps in the plan
workflow.add_conditional_edges(
    "agent",
    should_continue_plan,
    ["agent", "goal_assessor"],
)

# From goal assessor, we either end or replan
workflow.add_conditional_edges(
    "goal_assessor",
    route_after_assessment,
    ["replan", END],
)

workflow.add_conditional_edges(
    "replan",
    should_end,
    ["agent", END],
)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile()

config = {"recursion_limit": 50}
inputs = {
    "input": "Get me a list of the names of people who have been prominent in AI news this week, along with why they are in the news"
}


async def main():
    """Run the workflow."""
    final_result = ""
    goal_assessment_result = None
    async for event in app.astream(inputs, config=config):
        for k, v in event.items():
            if k != "__end__" and v is not None:
                if "plan" in v:
                    print("PLAN:")
                    for item in v["plan"]:
                        print(f"  - {item}")
                if "past_steps" in v:
                    for step, result in v["past_steps"]:
                        print(f"EXECUTED: {step}")
                        final_result += result + "\n"
                if "response" in v:
                    goal_assessment_result = v["response"]
    print("DONE: " + final_result)
    if goal_assessment_result:
        print("\nGOAL ASSESSMENT RESULT:")
        print(goal_assessment_result)


def show_graph():
    """Save graph flowchart."""
    graph = app.get_graph(xray=True)
    print(graph.draw_ascii())
    img_data = graph.draw_mermaid_png()
    img = PILImage.open(io.BytesIO(img_data))
    img.save("graph.png")


# Parse command line arguments
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Plan and Execute workflow")
    parser.add_argument("--flowchart", action="store_true", help="Generate flowchart image")
    return parser.parse_args()


# Check if running in a Jupyter Notebook
get_ipython = globals().get("get_ipython", None)
args = parse_args()

if get_ipython is not None:
    # Notebook: Always display the image
    display(Image(app.get_graph(xray=True).draw_mermaid_png()))
else:
    # Script: Save the image only if --flowchart flag is provided
    if args.flowchart:
        show_graph()
    asyncio.run(main())
