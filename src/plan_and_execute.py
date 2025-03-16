"""Plan and execute agent"""

# inspired by
#     https://colab.research.google.com/github/langchain-ai/langgraph/blob/main/docs/docs/tutorials/plan-and-execute/plan-and-execute.ipynb

import argparse
import asyncio
import datetime
import io
import json
import operator
import os
import re
from typing import Annotated, Dict, List, Tuple, Union
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

from workflows import load_flowchart_from_yaml


# Default model name for the LLM
MODEL_NAME = "gpt-4o"


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(description="different steps to follow, should be in sorted order")


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
    is_list_output: bool = Field(description="Whether the output should be a list (true) or a text object (false)")
    json_output: Union[List[str], Dict[str, str], str] = Field(
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
        self.agent_executor = create_react_agent(self.llm, self.tools, prompt=self.prompt)

        # Initialize prompts
        self._init_prompts()

        # Create the workflow
        self.app = self._build_workflow()

    def _create_search_tool(self):
        """Create the search tool"""

        @tool
        def search(query: str):
            """Call to surf the web using Tavily."""
            print(f"Tavily search: {query}")
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
                    Your plan should involve individual tasks, that if executed correctly will
                    yield the correct answer.
                    Today's date is {current_date}. It is very important to use the current date, 
                    {current_date}, when formulating searches.  
                    Remember, the date is {current_date}.  Always prioritize searching for 
                    information relevant to the *current* date and time.  
                    Never use a date other than today's date, {current_date}, when making searches.
                    Do NOT search for information from the past unless explicitly requested
                    by the user.
                    The plan should use the supplied tools when appropriate. The tools are """
                    + ", ".join([f"{tool.name}: {tool.description}" for tool in self.tools])
                    + """Do not add any superfluous steps.
                    If one step can do the work of several, use one step.
                    Do not request feedback or clarification from the user.
                    The result of the final step should be the final answer.
                    Ensure the final answer matches for format request, 
                    for example if asked for a list names, only return a list of names rather than
                    details ofr each name or a list of companies.
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
            Today's date is {current_date}. It is very important to use the current date, 
            {current_date}, when formulating searches.  
            Remember, the date is {current_date}.  Always prioritize searching for 
            information relevant to the *current* date and time.  
            Never use a date other than today's date, {current_date}, when making searches.
            Do NOT search for information from the past unless explicitly requested
            by the user.
            This plan should involve individual tasks, that if executed correctly
            will yield the correct answer. Do not add any superfluous steps.
            The plan should use the supplied tools when appropriate. The tools are """
            + ", ".join([f"{tool.name}: {tool.description}" for tool in self.tools])
            + """The result of the final step should be the final answer.
            Ensure the final answer matches for format request, 
            Do not request feedback or clarification from the user.
            for example if asked for a list names, only return a list of names rather than
            details ofr each name or a list of companies.
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

        If the goal was "Explain what AI is", your json_output should be a dictionary with a single key "response_text" and the value as your answer text.
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
        self.goal_assessor = self.goal_assessor_prompt | self.llm.with_structured_output(
            GoalAssessment, method="function_calling"
        )

    def _clean_result_text(self, result: str, max_length: int = 2000) -> str:
        """
        Clean and process result text to remove repetitive content and limit length.

        Args:
            result: The raw result text
            max_length: Maximum length to keep

        Returns:
            Cleaned and truncated result text
        """
        if not result:
            return ""

        # Detect repetitive request patterns (common in confused LLM outputs)
        repetitive_patterns = [
            r"(?:Please provide|I need).*?(?:paragraphs|text|information).*?(?:related to|about).*?(?:individual|person)",
            r"To (?:proceed|complete|execute).*?(?:step|task).*?(?:need|require).*?(?:paragraphs|text|information)",
            r"(?:Once you provide|If you provide).*?(?:information|content|text).*?(?:I can|I will)",
        ]

        # Check for repetitive content
        repetitive_content = False
        for pattern in repetitive_patterns:
            matches = re.findall(pattern, result, re.IGNORECASE)
            if len(matches) > 2:  # More than 2 similar requests indicates repetition
                repetitive_content = True
                break

        if repetitive_content:
            # Extract just the first part before repetition starts
            first_sentences = ". ".join(result.split(". ")[:5])
            return first_sentences + "... [Repetitive content truncated]"

        # Normal truncation for length
        return result[:max_length] + "..." if len(result) > max_length else result

    async def execute_step(self, state: PlanExecute):
        """Execute the first step in the plan and update the state"""
        # Steps is a stack and we execute the top item always,
        # then afterwards we pop the first step to past_steps.
        plan = state["plan"]
        past_steps = state.get("past_steps", [])

        # Format the past steps and their results for context, with token management
        past_steps_context = ""
        if past_steps:
            # If we have many steps, we need to be selective to avoid context length issues
            if len(past_steps) > 5:
                # Include a summary of all steps
                past_steps_context = "Summary of all previously completed steps:\n"
                for idx, (step, _) in enumerate(past_steps):
                    past_steps_context += f"Step {idx+1}: {step}\n"

                past_steps_context += "\nDetailed results of the most recent and relevant steps:\n"

                # Include full details of only the most recent steps
                recent_steps = past_steps[-3:]  # Last 3 steps
                for idx, (step, result) in enumerate(recent_steps):
                    full_idx = len(past_steps) - len(recent_steps) + idx + 1
                    past_steps_context += f"Step {full_idx}: {step}\n"
                    # Clean and truncate results to avoid context explosion
                    result_truncated = self._clean_result_text(result)
                    past_steps_context += f"Result of Step {full_idx}: {result_truncated}\n\n"
            else:
                # If we have few steps, include all details
                past_steps_context = "Previously completed steps and their results:\n"
                for idx, (step, result) in enumerate(past_steps):
                    past_steps_context += f"Step {idx+1}: {step}\n"
                    # Truncate very long results to avoid context explosion
                    result_truncated = self._clean_result_text(result)
                    past_steps_context += f"Result of Step {idx+1}: {result_truncated}\n\n"

        plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
        task = plan[0]
        current_date = datetime.datetime.now().strftime("%m/%d/%Y")
        task_formatted = f"""
            For the following plan:
            {plan_str}
            
            {past_steps_context}
            You are tasked with executing step {len(past_steps) + 1}, {task}, given the current date is {current_date}.
            IMPORTANT: Use the results of previous steps to inform your execution of this step.
            Do not describe the task before giving results and do not
            summarise after the task unless explicitly asked to do so."""
        agent_response = await self.agent_executor.ainvoke({"messages": [("user", task_formatted)]})
        remaining_plan = plan[1:] if len(plan) > 1 else []
        return {
            "past_steps": past_steps + [(task, agent_response["messages"][-1].content)],
            "plan": remaining_plan,
        }

    async def plan_step(self, state: PlanExecute):
        """Generate a new plan based on the current input"""
        current_date = datetime.datetime.now().strftime("%m/%d/%Y")
        plan = await self.planner.ainvoke({"messages": [("user", state["input"])], "current_date": current_date})
        return {"plan": plan.steps}

    async def replan_step(self, state: PlanExecute):
        """Replan based on the current state"""
        # Prepare the input for the replanner
        replanner_input = state.copy()

        # Add current date to the context
        replanner_input["current_date"] = datetime.datetime.now().strftime("%m/%d/%Y")

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
        plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(state.get("plan", [])))

        # Create a string representation of past steps
        past_steps_str = ""
        for step, step_result in state.get("past_steps", []):
            past_steps_str += f"Step: {step}\nResult: {step_result}\n\n"

        assessment = await self.goal_assessor.ainvoke(
            {"input": state["input"], "plan": plan_str, "past_steps": past_steps_str}
        )

        if assessment.is_satisfied:
            print("Goal satisfied!")
            # Format the response as JSON based on whether it should be a list or text object
            if assessment.is_list_output:
                # Ensure we have a JSON list
                if isinstance(assessment.json_output, list):
                    json_output = assessment.json_output
                else:
                    # Convert to list if it's not already a list
                    json_output = []
                print(f"JSON LIST OUTPUT: {json.dumps(json_output)}")
            else:
                # Ensure we have a JSON object with one entry
                if isinstance(assessment.json_output, dict):
                    json_output = assessment.json_output
                elif isinstance(assessment.json_output, str):
                    # If it's a string, wrap it in a dictionary
                    json_output = {"response_text": assessment.json_output}
                else:
                    # Default fallback
                    json_output = {"response_text": assessment.final_response}

                print(f"JSON OBJECT OUTPUT: {json_output}")

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

    # Flowchart-related functions
    async def load_flowchart_from_yaml(self, file_path: str):
        """
        Load a flowchart from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            The flowchart data as a dictionary
        """
        return await load_flowchart_from_yaml(file_path)

    async def build_custom_workflow_from_flowchart(self, _):
        """
        Build a custom workflow from a flowchart.

        Args:
            _: The flowchart data as a dictionary

        Returns:
            A StateGraph workflow
        """
        # This is a stub implementation for testing
        # In a real implementation, this would build a workflow from the flowchart
        return self.app

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

        try:
            # Run the workflow using the default app
            async for event in self.app.astream(inputs, config=config):
                for k, v in event.items():
                    if k != "__end__" and v is not None:
                        # Handle both direct and nested structures (for testing)
                        if "past_steps" in v:
                            # In plan execution, steps are moved to past_steps as they are completed
                            for step, result in v["past_steps"]:
                                print(f"EXECUTED: {step}")
                                # Add the result to final_result
                                final_result += result + "\n"
                        # Handle nested structure for agent events in tests
                        elif k == "agent" and isinstance(v, dict) and "past_steps" in v:
                            for step, result in v["past_steps"]:
                                print(f"EXECUTED: {step}")
                                # Add the result to final_result
                                final_result += result + "\n"

                        if "plan" in v:
                            # A plan has been created
                            print("PLAN:")
                            for idx, item in enumerate(v["plan"]):
                                print(f"  {idx+1}. {item}")
                        if "response" in v:
                            # The model response
                            goal_assessment_result = v["response"]
                        # Handle nested structure for goal_assessor events in tests
                        elif k == "goal_assessor" and isinstance(v, dict) and "response" in v:
                            goal_assessment_result = v["response"]

                        if "goal_assessment_feedback" in v:
                            # if the response was rejected, feedback is given as to why
                            goal_assessment_feedback = v["goal_assessment_feedback"]
                            print(f"\nGOAL ASSESSMENT FEEDBACK: {goal_assessment_feedback}")

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
    parser.add_argument("--flowchart", action="store_true", help="Generate flowchart image")
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
    # Import here to avoid circular imports
    from workflow_logger import log_workflow_execution

    # Record start time
    start_time = datetime.datetime.now()
    workflow_name = "Command Line Workflow"

    args = parse_args()

    try:
        # Create the agent
        agent = PlanAndExecuteAgent()

        # Save the image only if --flowchart flag is provided
        if args.flowchart:
            agent.show_graph()

        # Run the main workflow
        try:
            run_result = asyncio.run(agent.run(args.input))

            # Record end time
            end_time = datetime.datetime.now()

            # Log successful execution
            log_workflow_execution(
                workflow_name=workflow_name,
                start_time=start_time,
                end_time=end_time,
                result=run_result.get("final_result", ""),
            )

            # Check if there was an error
            if run_result.get("error"):
                print(f"\nExecution completed with error: {run_result.get('error')}")

        except KeyboardInterrupt:
            error_message = "Execution interrupted by user at the top level."
            print(f"\n{error_message}")
            print("Exiting gracefully...")

            # Record end time for interrupted execution
            end_time = datetime.datetime.now()

            # Log interrupted execution
            log_workflow_execution(
                workflow_name=workflow_name,
                start_time=start_time,
                end_time=end_time,
                result=None,
                success=False,
                error=error_message,
            )

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        import traceback

        # Record end time for error case
        end_time = datetime.datetime.now()

        # Log failed execution
        log_workflow_execution(
            workflow_name=workflow_name,
            start_time=start_time,
            end_time=end_time,
            result=None,
            success=False,
            error=str(e),
        )
        traceback.print_exc()
