# Plan and Execute Agent

This project implements the "Plan and Execute" approach to problem-solving with Large Language Models (LLMs) as described in the paper ["Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models"](https://arxiv.org/pdf/2305.04091) by Wang et al.

## Overview

Plan-and-Execute is a powerful paradigm for complex reasoning with LLMs that breaks down problem-solving into two distinct phases:

1. **Planning Phase**: The LLM first generates a step-by-step plan to solve the problem
2. **Execution Phase**: Each step of the plan is executed sequentially, with the ability to adapt the plan based on intermediate results

This approach has several advantages over monolithic prompting:
- Improves handling of complex, multi-step tasks
- Reduces reasoning errors by focusing on one step at a time
- Enables dynamic replanning when new information is discovered
- Provides better explainability through the explicit plan

My implementation differs in 2 key aspects:
1. **Goal Assessment**: A mechanism for assessing whether the original goal has been achieved.
2. **Less Replanning**: The agent can dynamically modify its plan if the goal is not achieved.


## Implementation

This implementation uses [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain) to create a flexible workflow that includes:

- **Planning**: Generate an initial step-by-step plan
- **Execution**: Execute each step using a ReAct agent with access to tools
- **Goal Assessment**: Evaluate if the original goal has been satisfied
- **Replanning**: Modify the plan based on execution results and feedback

The main components include:

- `StateGraph`: Manages the workflow and state transitions
- `PlanExecute` state: Tracks the current plan, executed steps, and results
- Tool integration (e.g., Tavily search API)
- Goal assessment to determine when the task is complete

## Requirements

- Python 3.8+
- OpenAI API key
- Tavily API key

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   TAVILY_API_KEY=your_tavily_key
   ```

## Usage

The main implementation is in `src/plan_and_execute.py`. You can run it with:

```bash
python src/plan_and_execute.py
```

To generate a visual flowchart of the workflow:

```bash
python src/plan_and_execute.py --flowchart
```

## Workflow

The workflow follows these steps:

1. **Initial Planning**: Generate a step-by-step plan for the given task
2. **Step Execution**: Execute the first step of the plan using a ReAct agent
3. **Goal Assessment**: Determine if the goal has been satisfied
4. **Conditional Routing**:
   - If there are more steps in the plan, continue execution
   - If the goal is satisfied, return the final response
   - If the goal is not satisfied but the plan is complete, replan

## Example

The default example task is:
```
"Get me a list of the names of people who have been prominent in AI news this week, along with why they are in the news"
```

The system will:
1. Generate a plan to search for recent AI news
2. Execute searches using the Tavily API
3. Extract relevant information about prominent people
4. Format the results as requested
5. Return a structured response

## Extending the Implementation

You can extend this implementation by:

1. Adding more tools to the agent
2. Customizing the planning and execution prompts
3. Modifying the state graph for more complex workflows
4. Implementing additional assessment or routing logic

## References

- [Plan-and-Solve Prompting Paper](https://arxiv.org/pdf/2305.04091)
- [LangGraph Plan-and-Execute Tutorial](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/)
- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [LangChain Documentation](https://github.com/langchain-ai/langchain)
