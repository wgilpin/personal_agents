""" Plan and execute agent """

# inspired by
#     https://colab.research.google.com/github/langchain-ai/langgraph/blob/main/docs/docs/tutorials/plan-and-execute/plan-and-execute.ipynb

import argparse
import asyncio
import io
import json
import operator
import os
from typing import Annotated, Dict, List, Optional, Tuple, Union

import yaml
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from PIL import Image as PILImage
from pydantic import BaseModel, Field
from tavily import TavilyClient
from typing_extensions import TypedDict

# Default model name for the LLM
MODEL_NAME = "gpt-4o"


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
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


class PlanExecute(TypedDict):
    """PlanExecute is used to track the current state of the agent"""

    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    goal_assessment_feedback: str


class PlanAndExecuteAgent:
    """Class that encapsulates the plan and execute agent functionality"""

    def __init__(self, model_name=MODEL_NAME):
        """Initialize the agent with necessary components"""
        # Load environment variables
        load_dotenv()

        # Initialize tools
        self.tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        self.tools = [self._create_search_tool()]

        # Initialize memory and LLM
        self.memory = MemorySaver()
        self.llm = ChatOpenAI(model=model_name)

        # Initialize agent executor
        self.prompt = "You are a helpful assistant."
        self.agent_executor = create_react_agent(
            self.llm, self.tools, prompt=self.prompt
        )

        # Initialize prompts
        self._init_prompts()

        # Create the workflow
        self.app = self._build_workflow()

    def _create_search_tool(self):
        """Create the search tool"""

        @tool
        def search(query: str):
            """Call to surf the web using Tavily."""
            return self.tavily_client.search(query)

        return search

    def _init_prompts(self):
        """Initialize all prompts used by the agent"""
        # Planner prompt
        self.planner_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """For the given objective, come up with a simple step by step plan.
                    This plan should involve individual tasks, that if executed correctly will
                    yield the correct answer.
                    The plan should use the supplied tools when appropriate. The tools are """
                    + ", ".join(
                        [f"{tool.name}: {tool.description}" for tool in self.tools]
                    )
                    + """Do not add any superfluous steps.
                    The result of the final step should be the final answer.
                    Make sure that each step has all the information needed - do not skip steps.""",
                ),
                ("placeholder", "{messages}"),
            ]
        )
        self.planner = self.planner_prompt | self.llm.with_structured_output(Plan)

        # Replanner prompt
        self.replanner_prompt = ChatPromptTemplate.from_template(
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

            Take account of the feedback provided:
            {goal_assessment_feedback_section}

            Update your plan accordingly.
            If no more steps are needed and you can return to the user, then respond with that.
            Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done.
            Do not return previously done steps as part of the plan, and do not add any steps that
            are effectively the same as steps that have already been done.
            """
        )
        self.replanner = self.replanner_prompt | self.llm.with_structured_output(Act)

        # Goal assessor prompt
        self.goal_assessor_system_template = """
        You are a goal assessment expert. Your job is to determine if the user's original goal has been satisfied 
        based on the work that has been done so far.

        IMPORTANT: Analyze if the goal is asking for a list or text:
        - If the goal is asking for a list (e.g., "list of people", "list of items", etc.), format your output as a JSON list.
        - If the goal is asking for text (e.g., explanation, description, etc.), format your output as a JSON object with one entry.

        For example, if the goal was "Get me a list of AI researchers", your json_output should be a list like:
        ["Geoffrey Hinton", "Yann LeCun", "Yoshua Bengio"]

        If the goal was "Explain what AI is", your json_output should be a json object with a single key & value. The key is  "response_text", the value is your answer as a text string.
        """

        self.goal_assessor_user_template = """
        Original goal: {input}

        Original plan: {plan}

        Steps completed: {past_steps}

        Based on the above information, has the original goal been fully satisfied? 
        If yes, provide a final response to the user that addresses their original goal.
        If no, explain why the goal hasn't been satisfied yet and what still needs to be done.
        """

        self.goal_assessor_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.goal_assessor_system_template),
                ("human", self.goal_assessor_user_template),
            ]
        )
        self.goal_assessor = (
            self.goal_assessor_prompt
            | self.llm.with_structured_output(GoalAssessment, method="function_calling")
        )

    async def execute_step(self, state: PlanExecute):
        """Execute the first step in the plan and update the state"""
        # Steps is a stack and we execute the top item always,
        # then afterwards we pop the first step to past_steps.
        plan = state["plan"]
        plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
        task = plan[0]
        task_formatted = f"""
            For the following plan:
            {plan_str}\n\nYou are tasked with executing step {1}, {task}."""
        agent_response = await self.agent_executor.ainvoke(
            {"messages": [("user", task_formatted)]}
        )
        # Pop the executed step from the plan onto past_steps
        remaining_plan = plan[1:] if len(plan) > 1 else []
        return {
            "past_steps": [(task, agent_response["messages"][-1].content)],
            "plan": remaining_plan,
        }

    async def plan_step(self, state: PlanExecute):
        """Generate a new plan based on the current input"""
        plan = await self.planner.ainvoke({"messages": [("user", state["input"])]})
        return {"plan": plan.steps}

    async def replan_step(self, state: PlanExecute):
        """Replan based on the current state"""
        # Prepare the input for the replanner
        replanner_input = state.copy()

        # Format the goal assessment feedback if it exists
        if "goal_assessment_feedback" in state and state["goal_assessment_feedback"]:
            replanner_input["goal_assessment_feedback_section"] = (
                f"Goal Assessment Feedback: {state['goal_assessment_feedback']}"
            )
        else:
            replanner_input["goal_assessment_feedback_section"] = ""

        output = await self.replanner.ainvoke(replanner_input)
        if isinstance(output.action, Response):
            print(f"Response : {output.action.response}")
            return {"response": output.action.response}
        else:
            print("REPLAN")
            for task in output.action.steps:
                print(f"- {task}")
            return {"plan": output.action.steps}

    async def assess_goal(self, state: PlanExecute):
        """Assess if the goal has been satisfied based on the completed steps"""
        # Create a string representation of the plan for the prompt
        plan_str = "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(state.get("plan", []))
        )

        # Create a string representation of past steps
        past_steps_str = ""
        for step, result in state.get("past_steps", []):
            past_steps_str += f"Step: {step}\nResult: {result}\n\n"

        assessment = await self.goal_assessor.ainvoke(
            {"input": state["input"], "plan": plan_str, "past_steps": past_steps_str}
        )

        if assessment.is_satisfied:
            print("Goal satisfied!")
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
            # Return the assessment feedback to be used by the replanner
            return {"goal_assessment_feedback": assessment.final_response}

    def should_continue_plan(self, state: PlanExecute):
        """Check if there are more steps in the plan to execute"""
        # Conditional Edge. return the next node to execute
        if state["plan"]:
            return "agent"
        else:
            return "goal_assessor"

    def should_end(self, state: PlanExecute):
        """Check if the workflow should end"""
        # Conditional Edge. return the next node to execute
        if "response" in state and state["response"]:
            return END
        else:
            return "agent"

    def route_after_assessment(self, state: PlanExecute):
        """Determine next step after goal assessment"""
        # Conditional Edge. return the next node to execute
        if "response" in state and state["response"]:
            return END
        else:
            return "replan"

    def _build_workflow(self):
        """Build the workflow graph"""
        workflow = StateGraph(PlanExecute)

        # Add the plan node
        workflow.add_node("planner", self.plan_step)

        # Add the execution step
        workflow.add_node("agent", self.execute_step)

        # Add the goal assessment node
        workflow.add_node("goal_assessor", self.assess_goal)

        # Add a replan node
        workflow.add_node("replan", self.replan_step)

        workflow.add_edge(START, "planner")

        # From plan we go to agent
        workflow.add_edge("planner", "agent")

        # From agent, we check if there are more steps in the plan
        workflow.add_conditional_edges(
            "agent",
            self.should_continue_plan,
            ["agent", "goal_assessor"],
        )

        # From goal assessor, we either end or replan
        workflow.add_conditional_edges(
            "goal_assessor",
            self.route_after_assessment,
            ["replan", END],
        )

        workflow.add_conditional_edges(
            "replan",
            self.should_end,
            ["agent", END],
        )

        # Compile it into a LangChain Runnable
        return workflow.compile()

    async def load_flowchart_from_yaml(self, filepath: str) -> Optional[Dict]:
        """
        Load a flowchart from a YAML file.

        Args:
            filepath: Path to the YAML file.

        Returns:
            Dictionary containing the flowchart data if the file exists, None otherwise.
        """
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                flowchart_data = yaml.safe_load(f)
            return flowchart_data
        except Exception as e:
            print(f"Error loading flowchart from {filepath}: {str(e)}")
            return None

    async def build_custom_workflow_from_flowchart(
        self, flowchart_data: Dict
    ) -> StateGraph:
        """
        Build a custom workflow from flowchart data.

        Args:
            flowchart_data: Dictionary containing the flowchart data.

        Returns:
            A StateGraph object representing the custom workflow.
        """
        # Create a new StateGraph
        custom_workflow = StateGraph(PlanExecute)

        # Map of node IDs to their types
        node_types = {}

        # Add nodes from the flowchart
        for node in flowchart_data.get("nodes", []):
            node_id = node.get("id")
            node_type = node.get("type")
            node_content = node.get("content", "")

            # Store node type for later use
            node_types[node_id] = node_type

            # Add the node to the graph based on its type
            if node_type == "act":
                # Action nodes execute a command
                custom_workflow.add_node(node_id, self.execute_step)
            elif node_type == "choice":
                # Choice nodes make a decision
                custom_workflow.add_node(node_id, self.assess_goal)
            elif node_type == "terminal":
                # Terminal nodes end the workflow
                # We don't add these as nodes, but use them as endpoints
                pass

        # Add connections from the flowchart
        for connection in flowchart_data.get("connections", []):
            from_node_id = connection.get("from", {}).get("nodeId")
            to_node_id = connection.get("to", {}).get("nodeId")

            # Skip if either node doesn't exist
            if from_node_id not in node_types or to_node_id not in node_types:
                continue

            # Add edge based on node types
            if node_types[from_node_id] == "choice":
                # For choice nodes, we add conditional edges
                custom_workflow.add_conditional_edges(
                    from_node_id, self.route_after_assessment, [to_node_id, END]
                )
            else:
                # For other nodes, we add direct edges
                custom_workflow.add_edge(from_node_id, to_node_id)

        # Add the START edge to the first node (assuming the first node in the list is the start)
        if flowchart_data.get("nodes"):
            first_node_id = flowchart_data["nodes"][0]["id"]
            custom_workflow.add_edge(START, first_node_id)

        # Compile the workflow
        return custom_workflow.compile()

    async def run(self, input_text: str, config: Dict = None):
        """
        Run the workflow with the given input.

        Args:
            input_text: The input text to process.
            config: Optional configuration for the workflow.

        Returns:
            The final result of the workflow.
        """
        if config is None:
            config = {"recursion_limit": 50}

        inputs = {"input": input_text}
        final_result = ""
        goal_assessment_result = None
        goal_assessment_feedback = None

        # Check if there's a flowchart YAML file
        flowchart_path = os.path.join(
            os.path.dirname(__file__), "flowcharts", "current_flowchart.yaml"
        )
        flowchart_data = await self.load_flowchart_from_yaml(flowchart_path)

        # Determine which workflow to use
        workflow_to_use = self.app  # Default workflow

        if flowchart_data:
            print(f"Using flowchart from {flowchart_path}")
            try:
                # Build a custom workflow from the flowchart
                custom_workflow = await self.build_custom_workflow_from_flowchart(
                    flowchart_data
                )
                workflow_to_use = custom_workflow
                print("Successfully built custom workflow from flowchart")
            except Exception as e:
                print(f"Error building custom workflow: {str(e)}")
                print("Falling back to default workflow")

        try:
            # Run the workflow
            async for event in workflow_to_use.astream(inputs, config=config):
                for k, v in event.items():
                    if k != "__end__" and v is not None:
                        if "past_steps" in v:
                            # In plan execution, steps are moved to past_steps as they are completed
                            for step, result in v["past_steps"]:
                                print(f"EXECUTED: {step}")
                                final_result += result + "\n"
                        if "plan" in v:
                            # A plan has been created
                            print("PLAN:")
                            for idx, item in enumerate(v["plan"]):
                                print(f"  {idx+1}. {item}")
                        if "response" in v:
                            # The model response
                            goal_assessment_result = v["response"]
                        if "goal_assessment_feedback" in v:
                            # if the response was rejected, feedback is given as to why
                            goal_assessment_feedback = v["goal_assessment_feedback"]
                            print(
                                f"\nGOAL ASSESSMENT FEEDBACK: {goal_assessment_feedback}"
                            )

            print("DONE: " + final_result)
            if goal_assessment_result:
                # the final json result of the model
                print("\nGOAL ASSESSMENT RESULT:")
                print(goal_assessment_result)

        except KeyboardInterrupt:
            print("\n\nExecution interrupted by user. Cleaning up...")
            # You might want to add additional cleanup code here if needed
            return {
                "final_result": final_result,
                "goal_assessment_result": goal_assessment_result,
                "goal_assessment_feedback": "Execution was interrupted by user",
                "error": "KeyboardInterrupt",
            }
        except Exception as e:
            print(f"\n\nAn error occurred during execution: {str(e)}")
            return {
                "final_result": final_result,
                "goal_assessment_result": goal_assessment_result,
                "goal_assessment_feedback": f"Execution failed with error: {str(e)}",
                "error": str(e),
            }

        return {
            "final_result": final_result,
            "goal_assessment_result": goal_assessment_result,
            "goal_assessment_feedback": goal_assessment_feedback,
        }

    def show_graph(self, output_path="graph.png"):
        """
        Save graph flowchart.

        Args:
            output_path: Path to save the graph image.
        """
        graph = self.app.get_graph(xray=True)
        print(graph.draw_ascii())
        img_data = graph.draw_mermaid_png()
        img = PILImage.open(io.BytesIO(img_data))
        img.save(output_path)


# Command-line interface for running the agent
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Plan and Execute workflow")
    parser.add_argument(
        "--flowchart", action="store_true", help="Generate flowchart image"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="""Get me a list of the names of people who have been prominent in AI news this week, along with
            why they are in the news""",
        help="Input text to process",
    )
    return parser.parse_args()


# Only run the main function if this script is executed directly, not when imported
if __name__ == "__main__":
    args = parse_args()

    try:
        # Create the agent
        agent = PlanAndExecuteAgent()

        # Save the image only if --flowchart flag is provided
        if args.flowchart:
            agent.show_graph()

        # Run the main workflow
        try:
            result = asyncio.run(agent.run(args.input))

            # Check if there was an error
            if result.get("error"):
                print(f"\nExecution completed with error: {result['error']}")

        except KeyboardInterrupt:
            print("\nExecution interrupted by user at the top level.")
            print("Exiting gracefully...")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        import traceback

        traceback.print_exc()
