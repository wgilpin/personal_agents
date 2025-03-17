#!/usr/bin/env python
"""Script to run test coverage for the Plan and Execute agent"""

import os
import sys
import subprocess
import pytest

try:
    import pytest_cov
except ImportError:
    print("pytest-cov not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest-cov"])
    import pytest_cov


def main():
    """Run tests with coverage"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Add both the script directory and project root to the Python path
    sys.path.insert(0, script_dir)
    sys.path.insert(0, project_root)

    # Identify all Python modules in the src directory
    modules = []
    for filename in os.listdir(script_dir):
        if filename.endswith(".py") and not filename.startswith("test_") and not filename == "run_coverage.py":
            module_name = filename[:-3]  # Remove .py extension
            modules.append(module_name)

    # Build coverage arguments
    cov_args = []
    for module in modules:
        cov_args.append(f"--cov={module}")

    # Run the backend tests with coverage
    test_files = [
        os.path.join(script_dir, "test_plan_and_execute.py"),
        os.path.join(script_dir, "test_integration.py"),
        os.path.join(script_dir, "test_api_server.py"),
        os.path.join(script_dir, "test_workflow_execution.py"),
    ]

    print("Running backend tests with coverage...")
    result = pytest.main(
        [
            "-xvs",
            *cov_args,  # Add coverage for each module
            "--cov-config=.coveragerc",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=xml",
        ]
        + test_files
    )

    if result == 0:
        print("\nCoverage report generated successfully!")
        print(f"HTML report available at: {os.path.join(project_root, 'htmlcov/index.html')}")
        print(f"XML report available at: {os.path.join(project_root, 'coverage.xml')}")
    else:
        print("\nTests failed or coverage report generation failed.")

    return result


if __name__ == "__main__":
    sys.exit(main())
