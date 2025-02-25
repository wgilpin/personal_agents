#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API server for plan_and_execute.py"""

import json
from typing import Dict, Any

import uvicorn # pylint: disable=import-error

from fastapi import FastAPI, HTTPException # pylint: disable=import-error
from pydantic import BaseModel
from dotenv import load_dotenv

from plan_and_execute import app, config

# Load environment variables before importing from plan_and_execute.py
load_dotenv()

# Create FastAPI app
api = FastAPI(title="Plan and Execute API", description="API for plan_and_execute.py")


class PromptInput(BaseModel):
    """Input model for the execute endpoint."""

    input: str


class ApiResponse(BaseModel):
    """Response model for the execute endpoint."""

    goal_assessment_result: Any


@api.post("/execute", response_model=ApiResponse)
async def execute_prompt(prompt_input: PromptInput) -> Dict[str, Any]:
    """
    Execute a prompt using the plan_and_execute workflow.

    Args:
        prompt_input: The input prompt.

    Returns:
        A dictionary containing the goal_assessment_result.
    """
    try:
        # Create inputs dictionary
        inputs = {"input": prompt_input.input}

        # Initialize goal_assessment_result
        goal_assessment_result = None

        # Execute the workflow
        async for event in app.astream(inputs, config=config):
            for k, v in event.items():
                if k != "__end__" and v is not None:
                    if "response" in v:
                        # The model response (goal_assessment_result)
                        goal_assessment_result = v["response"]

        # Check if goal_assessment_result is None
        if goal_assessment_result is None:
            raise HTTPException(
                status_code=500, detail="Failed to generate goal assessment result"
            )

        # Return the goal_assessment_result
        return {"goal_assessment_result": json.loads(goal_assessment_result)}

    except Exception as e:
        # Handle exceptions
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


# Run the server
if __name__ == "__main__":
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)
