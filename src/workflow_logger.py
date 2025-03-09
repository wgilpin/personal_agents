#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Logging functionality for workflow executions."""

import os
import json
import datetime
from typing import Any, Dict, Optional


def log_workflow_execution(
    workflow_name: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    result: Any,
    success: bool = True,
    error: Optional[str] = None,
) -> str:
    """
    Log a workflow execution to a file.

    Args:
        workflow_name: Name of the workflow that was executed
        start_time: When the workflow execution started
        end_time: When the workflow execution ended
        result: The final result value of the workflow execution
        success: Whether the execution was successful
        error: Error message if the execution failed

    Returns:
        Path to the log file that was written
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Format the log entry
    log_entry = {
        "workflow_name": workflow_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "success": success,
        "result": result,
    }

    if error:
        log_entry["error"] = error

    # Create a filename with timestamp
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    safe_workflow_name = "".join(c if c.isalnum() else "_" for c in workflow_name)
    log_filename = f"{timestamp}_{safe_workflow_name}.json"
    log_path = os.path.join(logs_dir, log_filename)

    # Write the log entry to the file
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)

    return log_path
