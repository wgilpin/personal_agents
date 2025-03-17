#!/usr/bin/env python
"""Script to run all test coverage (backend and frontend) for the Plan and Execute agent"""

import os
import sys
import subprocess
import time
import webbrowser


def run_backend_coverage():
    """Run backend tests with coverage"""
    print("\n=== Running Backend Coverage Tests ===\n")
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Run the coverage script
    coverage_script = os.path.join(script_dir, "run_coverage.py")
    result = subprocess.run([sys.executable, coverage_script], check=False)

    if result.returncode != 0:
        print("\nBackend coverage tests failed!")
        return result.returncode

    return 0


def run_frontend_coverage():
    """Run frontend tests with coverage"""
    print("\n=== Running Frontend Coverage Tests ===\n")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vue_app_dir = os.path.join(script_dir, "ui", "vue-app")

    # Check if the directory exists
    if not os.path.isdir(vue_app_dir):
        print(f"Vue app directory not found at {vue_app_dir}")
        return 1

    # Run the frontend tests with coverage
    result = subprocess.run("npm run test:coverage", cwd=vue_app_dir, shell=True, check=False)

    if result.returncode != 0:
        print("\nFrontend coverage tests failed!")
        return result.returncode

    return 0


def open_coverage_reports():
    """Open the coverage reports in the default browser"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Backend coverage report
    backend_report = os.path.join(project_root, "htmlcov", "index.html")
    if os.path.exists(backend_report):
        print(f"\nOpening backend coverage report: {backend_report}")
        webbrowser.open(f"file://{backend_report}")

    # Frontend coverage report
    frontend_report = os.path.join(script_dir, "ui", "vue-app", "coverage", "lcov-report", "index.html")
    if os.path.exists(frontend_report):
        print(f"\nOpening frontend coverage report: {frontend_report}")
        # Wait a bit before opening the second report
        time.sleep(1)
        webbrowser.open(f"file://{frontend_report}")


def main():
    """Run all tests with coverage"""
    # Run backend coverage
    backend_result = run_backend_coverage()

    # Run frontend coverage
    frontend_result = run_frontend_coverage()

    # Print summary
    print("\n=== Coverage Test Summary ===\n")
    print(f"Backend tests: {'PASSED' if backend_result == 0 else 'FAILED'}")
    print(f"Frontend tests: {'PASSED' if frontend_result == 0 else 'FAILED'}")

    # Open coverage reports if tests passed
    if backend_result == 0 or frontend_result == 0:
        open_coverage_reports()

    # Return non-zero if any tests failed
    if backend_result != 0:
        return backend_result

    if frontend_result != 0:
        return frontend_result

    print("\nAll coverage tests completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
