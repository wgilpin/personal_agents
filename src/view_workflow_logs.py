#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility to view workflow execution logs."""

import os
import json
import argparse
import datetime
from typing import Dict, List, Optional


def list_log_files(logs_dir: str) -> List[str]:
    """
    List all log files in the logs directory.

    Args:
        logs_dir: Path to the logs directory

    Returns:
        List of log file paths
    """
    if not os.path.exists(logs_dir):
        return []

    log_files = []
    for filename in os.listdir(logs_dir):
        if filename.endswith(".json"):
            log_files.append(os.path.join(logs_dir, filename))

    # Sort by timestamp (newest first)
    log_files.sort(reverse=True)
    return log_files


def parse_log_file(log_path: str) -> Dict:
    """
    Parse a log file and return its contents.

    Args:
        log_path: Path to the log file

    Returns:
        Dictionary containing the log data
    """
    with open(log_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_log_entry(log_data: Dict, verbose: bool = False) -> str:
    """
    Format a log entry for display.

    Args:
        log_data: Dictionary containing the log data
        verbose: Whether to include the full result

    Returns:
        Formatted log entry as a string
    """
    # Parse timestamps
    start_time = datetime.datetime.fromisoformat(log_data["start_time"])
    end_time = datetime.datetime.fromisoformat(log_data["end_time"])

    # Format basic info
    formatted = f"Workflow: {log_data['workflow_name']}\n"
    formatted += f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    formatted += f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    formatted += f"Duration: {log_data['duration_seconds']:.2f} seconds\n"
    formatted += f"Status: {'Success' if log_data.get('success', True) else 'Failed'}\n"

    # Add error if present
    if "error" in log_data and log_data["error"]:
        formatted += f"Error: {log_data['error']}\n"

    # Add result if verbose
    if verbose and "result" in log_data and log_data["result"]:
        formatted += "\nResult:\n"
        # Try to pretty-print JSON if possible
        try:
            if isinstance(log_data["result"], str):
                result_obj = json.loads(log_data["result"])
                formatted += json.dumps(result_obj, indent=2)
            else:
                formatted += json.dumps(log_data["result"], indent=2)
        except (json.JSONDecodeError, TypeError):
            formatted += str(log_data["result"])

    return formatted


def filter_logs(
    log_files: List[str],
    workflow_name: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    success_only: bool = False,
    failed_only: bool = False,
) -> List[str]:
    """
    Filter log files based on criteria.

    Args:
        log_files: List of log file paths
        workflow_name: Filter by workflow name
        start_date: Filter by start date (inclusive)
        end_date: Filter by end date (inclusive)
        success_only: Only show successful executions
        failed_only: Only show failed executions

    Returns:
        Filtered list of log file paths
    """
    filtered_logs = []

    for log_path in log_files:
        try:
            log_data = parse_log_file(log_path)

            # Filter by workflow name
            if workflow_name and workflow_name.lower() not in log_data.get("workflow_name", "").lower():
                continue

            # Filter by success/failure
            if success_only and not log_data.get("success", True):
                continue
            if failed_only and log_data.get("success", True):
                continue

            # Filter by date range
            log_start_time = datetime.datetime.fromisoformat(log_data["start_time"])
            if start_date and log_start_time < start_date:
                continue
            if end_date and log_start_time > end_date:
                continue

            filtered_logs.append(log_path)
        except Exception as e:
            print(f"Error parsing log file {log_path}: {str(e)}")

    return filtered_logs


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="View workflow execution logs")
    parser.add_argument("--list", action="store_true", help="List all log files")
    parser.add_argument("--view", type=str, help="View a specific log file")
    parser.add_argument("--workflow", type=str, help="Filter by workflow name")
    parser.add_argument("--start-date", type=str, help="Filter by start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Filter by end date (YYYY-MM-DD)")
    parser.add_argument("--success", action="store_true", help="Show only successful executions")
    parser.add_argument("--failed", action="store_true", help="Show only failed executions")
    parser.add_argument("--verbose", action="store_true", help="Show full result details")
    parser.add_argument("--latest", action="store_true", help="Show only the latest log")
    args = parser.parse_args()

    # Get the logs directory
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)

    # Get all log files
    all_log_files = list_log_files(logs_dir)

    if not all_log_files:
        print("No log files found.")
        return

    # Parse date filters
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD.")
            return

    end_date = None
    if args.end_date:
        try:
            end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d")
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            print(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD.")
            return

    # Filter logs
    filtered_logs = filter_logs(
        all_log_files,
        workflow_name=args.workflow,
        start_date=start_date,
        end_date=end_date,
        success_only=args.success,
        failed_only=args.failed,
    )

    if not filtered_logs:
        print("No logs match the specified filters.")
        return

    # View a specific log file
    if args.view:
        log_path = args.view
        if not os.path.exists(log_path):
            # Try to find the log file by name in the logs directory
            for file_path in all_log_files:
                if os.path.basename(file_path) == args.view:
                    log_path = file_path
                    break
            else:
                print(f"Log file not found: {args.view}")
                return

        try:
            log_data = parse_log_file(log_path)
            print(format_log_entry(log_data, verbose=args.verbose))
        except Exception as e:
            print(f"Error parsing log file {log_path}: {str(e)}")
        return

    # Show only the latest log
    if args.latest:
        if filtered_logs:
            latest_log = filtered_logs[0]  # Already sorted newest first
            try:
                log_data = parse_log_file(latest_log)
                print(format_log_entry(log_data, verbose=args.verbose))
            except Exception as e:
                print(f"Error parsing log file {latest_log}: {str(e)}")
        return

    # List all log files
    if args.list or not (args.view or args.latest):
        print(f"Found {len(filtered_logs)} log files:")
        for i, log_path in enumerate(filtered_logs):
            try:
                log_data = parse_log_file(log_path)
                start_time = datetime.datetime.fromisoformat(log_data["start_time"])
                status = "Success" if log_data.get("success", True) else "Failed"
                print(f"{i+1}. {os.path.basename(log_path)}")
                print(f"   Workflow: {log_data['workflow_name']}")
                print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Status: {status}")
                print()
            except Exception as e:
                print(f"{i+1}. {os.path.basename(log_path)} (Error: {str(e)})")


if __name__ == "__main__":
    main()
