#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API server for plan_and_execute.py"""

import json
import os
import yaml
from typing import Dict, Any, Optional

import uvicorn # pylint: disable=import-error

from fastapi import FastAPI, HTTPException, File, UploadFile # pylint: disable=import-error
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from plan_and_execute import app, config

# Load environment variables before importing from plan_and_execute.py
load_dotenv()

# Create FastAPI app
api = FastAPI(title="Plan and Execute API", description="API for plan_and_execute.py")

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


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


class FlowchartResponse(BaseModel):
    """Response model for the flowchart endpoint."""

    success: bool
    message: str


@api.post("/flowchart", response_model=FlowchartResponse)
async def upload_flowchart(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a YAML flowchart file to be used by the AI server.

    Args:
        file: The YAML file containing the flowchart data.

    Returns:
        A dictionary indicating success or failure.
    """
    try:
        # Check if the file is a YAML file
        if not file.filename.endswith(('.yaml', '.yml')):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "File must be a YAML file"}
            )

        # Read the file content
        content = await file.read()
        
        # Parse the YAML content to validate it
        try:
            flowchart_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Invalid YAML format: {str(e)}"}
            )

        # Save the file to a specific location
        flowchart_dir = os.path.join(os.path.dirname(__file__), 'flowcharts')
        os.makedirs(flowchart_dir, exist_ok=True)
        
        flowchart_path = os.path.join(flowchart_dir, 'current_flowchart.yaml')
        
        with open(flowchart_path, 'wb') as f:
            f.write(content)

        return {"success": True, "message": f"Flowchart saved successfully at {flowchart_path}"}

    except Exception as e:
        # Handle exceptions
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"An error occurred: {str(e)}"}
        )


# Run the server
if __name__ == "__main__":
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)
