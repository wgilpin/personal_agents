# %%
import operator
import os
import json
from typing import Annotated, List, Tuple, Optional, Dict, TypedDict, Union, Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from tavily import TavilyClient  # pylint: disable=import-error


# %%
load_dotenv()

# %%
# %%


class Plan(BaseModel):
    """Plan for a task."""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )
    past_steps: Annotated[List[Tuple], operator.add]


class Response(Plan):
    """Response to a task."""

    final_answer: Optional[str] = None
    final_answer_json: Optional[Union[List[Any], Dict[str, Any]]] = None
    is_list_output: bool = Field(
        default=False, 
        description="Whether the output should be a list (true) or a text object (false)"
    )


class AgentState(TypedDict):
    """ The state that persists across the task """
    messages: List[Any]  # Added messages field
    goal: Optional[str]
    plan: Optional[Plan]
    final_answer: Optional[str]
    final_answer_json: Optional[Union[List[Any], Dict[str, Any]]]
    is_list_output: bool


class AgentAction(BaseModel):
    """Action model for the agent."""
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None


model = ChatAnthropic(model_name="claude-3-haiku-20240307")

planning_model_with_structured_output = model.with_structured_output(Plan)
response_model_with_structured_output = model.with_structured_output(Response)


# %%
memory = MemorySaver()


tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@tool
def search(query: str):
    """Call to surf the web using Tavily."""
    return tavily_client.search(query)


tools = [search]
tool_node = ToolNode(tools)
action_model = model.bind(tools=tools, tool_choice="any")


# %%
def should_continue(state: AgentState):
    """Return the next node to execute."""
    last_message = state["messages"][-1]
    # If there is no function call, then go to final response
    if not last_message.tool_calls and len(state["plan"].steps) == 0:
        print("should_continue: No tool call.")
        return "make_final_response"
    # Otherwise if there is, we continue to action
    print("should_continue: Check plan")
    return "check_plan"

def more_plan_steps(state: AgentState):
    """Are there more plan steps remaining."""
    plan = state["plan"]
    if len(plan.steps) > 0:
        print("more_plan_steps: Act")
        return "agent"
    # If there is no more steps, then go to final response
    print("more_plan_steps: No more steps.")
    return "make_final_response"


# Define the function that calls the model
def call_model(state: AgentState):
    """Call the model and handle tool results."""
    response = action_model.invoke(state["messages"])
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


def build_plan(state: AgentState):
    """Build a plan."""
    # This is a test comment
    response = planning_model_with_structured_output.invoke(
        [
            HumanMessage(
                content="""For the given objective, come up with a simple step by step plan. \
            This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
            The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.
            """
            f"The final goal is: {state['goal']}"
            )
        ]
    )
    # We return the plan
    print(f"Plan from build_plan: {response}")
    return {"plan": response}


def update_plan(state: AgentState):
    """check if the plan is complete and update state"""
    # if not, return the plan from step 2
    if state["plan"] is None or len(state["plan"].steps) == 0:
        print("update_plan: No more steps in the plan.")
        return {"plan": Plan (steps=[])}
    else:
        # return the plan but remove the first item from the list
        print(f"update_plan: Removing first step from the plan: {state['plan'].steps[0]}")
        remaining_plan_steps = state["plan"].steps[1:]
        past_steps = state["plan"].past_steps + [(state["plan"].steps[0],)]
        return {**state, "plan": Plan(steps=remaining_plan_steps, past_steps=past_steps)}

def make_final_response(state: AgentState):
    """Make a final_answer as structured output."""
    # Determine if the goal is asking for a list or text
    goal = state.get("goal", "")
    is_list_output = any(keyword in goal.lower() for keyword in ["list", "names", "people", "items"])
    
    # Extract data from tool output if available
    tool_output = state["messages"][-2] if len(state["messages"]) > 1 else None
    articles = []
    if isinstance(tool_output, ToolMessage):
        tool_call_output_str = tool_output.content
        if tool_call_output_str:
            try:
                tool_call_output = json.loads(tool_call_output_str)
                if "results" in tool_call_output:
                    articles = tool_call_output["results"]
            except json.JSONDecodeError:
                # Handle case where tool output is not valid JSON
                pass

    # Format the response based on whether it should be a list or text
    if is_list_output:
        # If it's a list output (e.g., list of people, items)
        if articles:
            # Extract names or relevant items from articles
            names = []
            for article in articles:
                # Extract names from title or content if available
                title = article.get('title', '')
                if 'people' in names:
                    # This is a simplistic approach - in a real system, you'd use NER
                    # to extract actual person names from the content
                    names.append(title.split()[0] if title else "Unknown")
                else:
                    names.append(title if title else "Unknown")
            
            final_answer_json = names
            final_answer_str = "Here are the names from the AI news:\n" + "\n".join(f"- {name}" for name in names)
        else:
            final_answer_json = []
            final_answer_str = "No relevant information found in the search results."
    else:
        # If it's a text output (e.g., explanation, description)
        if articles:
            # Combine article information into a text summary
            summary = "Based on the search results:\n\n"
            for article in articles:
                title = article.get('title', 'Untitled')
                summary += f"- {title}\n"
            
            final_answer_json = {"text": summary}
            final_answer_str = summary
        else:
            final_answer_json = {"text": "No relevant information found in the search results."}
            final_answer_str = "No relevant information found in the search results."

    # Print the formatted output
    if is_list_output:
        print(f"JSON LIST OUTPUT: {json.dumps(final_answer_json)}")
    else:
        print(f"JSON OBJECT OUTPUT: {json.dumps(final_answer_json)}")

    response = {
        "final_answer": final_answer_str,
        "final_answer_json": final_answer_json,
        "is_list_output": is_list_output
    }
    return response


# Define a new graph
workflow = StateGraph(AgentState)

# add the planning node
workflow.add_node("planner", build_plan)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)


# Set the entrypoint as `build_plan`
# This means that this node is the first one called
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")

# We now add a conditional edge for the tools calls
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
    # Next, we pass in the path map - all the possible nodes this edge could go to
    ["action", "check_plan", "make_final_response"],
)

workflow.add_node("check_plan", update_plan)

# We now add a conditional edge for the plan steps completion
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "check_plan",
    # Next, we pass in the function that will determine which node is called next.
    more_plan_steps,
    # Next, we pass in the path map - all the possible nodes this edge could go to
    ["agent", "make_final_response"],
)

workflow.add_node("make_final_response", make_final_response)
workflow.add_edge("make_final_response", END)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge("action", "agent")

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile(checkpointer=memory)

# %%

# display the graph as an image
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod

display(
    Image(
        app.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
    )
)

# %%

config = {"configurable": {"thread_id": "2"}}

human_goal = "What people has been in the AI news in the last week?"

input_message = SystemMessage(
    content="""
    You are an AI assistant.
    Your task is to help the user with their goal.
    Return a final response in json structured form."""
)
initial_goal = HumanMessage(content=human_goal)

# Run the graph using app.invoke() and get the final state
final_state = app.invoke(
    {"messages": [input_message, initial_goal], "goal": human_goal}, config
)

# Print the entire final state dictionary
print("Final State Dictionary:")
print(final_state)

# Access specific attributes from the final state based on your AgentState definition
print("\nMessages in Final State:")
print(final_state["messages"][-1])  # Print the last message in the messages history

if (
    "plan" in final_state and final_state["plan"]
):  # Check if 'plan' exists and is not None
    print("\nPlan in Final State:")
    print(final_state["plan"])

# Check if 'final_answer_json' exists and is not None
if "final_answer_json" in final_state and final_state["final_answer_json"]:
    print("\nFinal Answer JSON in Final State:")
    print(final_state["final_answer_json"])
else:
    print("\nNo Final Answer JSON in Final State.")

# # %%
# # Stream the output
# for event in app.stream(
#     {"messages": [input_message, initial_goal], "goal": initial_goal}, config, stream_mode="values"
# ):
#     event["messages"][-1].pretty_print()

# # print the final state value
# print(app.store.value)
