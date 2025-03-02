"""Script to run all tests for the Plan and Execute agent"""

import os
import sys
import subprocess
import pytest  # pylint: disable=import-error


def run_frontend_tests():
    """Run frontend tests"""
    print("\nRunning frontend tests...")
    vue_app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "vue-app")
    result = subprocess.run(["npm", "run", "test"], cwd=vue_app_dir)
    return result.returncode


def main():
    """Run all tests"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Add the script directory to the Python path
    sys.path.insert(0, script_dir)

    # Run the backend tests
    test_files = [
        os.path.join(script_dir, "test_plan_and_execute.py"),
        os.path.join(script_dir, "test_integration.py"),
        os.path.join(script_dir, "test_api_server.py"),
    ]

    print("Running backend tests for the Plan and Execute agent...")
    backend_result = pytest.main(["-xvs"] + test_files)

    # Run the frontend tests
    frontend_result = run_frontend_tests()

    # Return non-zero if any tests failed
    if backend_result != 0:
        print("\nBackend tests failed!")
        return backend_result

    if frontend_result != 0:
        print("\nFrontend tests failed!")
        return frontend_result

    print("\nAll tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
