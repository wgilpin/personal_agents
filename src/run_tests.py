"""Script to run all tests for the Plan and Execute agent"""

import os
import sys
import pytest  # pylint: disable=import-error


def main():
    """Run all tests"""
    # Get the directory of this script``
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Add the script directory to the Python path
    sys.path.insert(0, script_dir)

    # Run the tests
    test_files = [
        os.path.join(script_dir, "test_plan_and_execute.py"),
        os.path.join(script_dir, "test_integration.py"),
        os.path.join(script_dir, "test_api_server.py"),
    ]

    print("Running tests for the Plan and Execute agent...")
    result = pytest.main(["-xvs"] + test_files)

    return result


if __name__ == "__main__":
    sys.exit(main())
