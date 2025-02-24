#!/usr/bin/env python3
"""
A simple script that accepts any prompt from the user and uses LangGraph
to execute it with available tools.
"""

# Use the correct import path based on the package structure.
from langgraph.client import LangGraph

def web_search(query: str) -> str:
    return f"[web-search] Results for '{query}' (simulated)."

def check_url_exists(url: str) -> str:
    return f"[check-url-exists] URL '{url}' exists (simulated)."

def get_drive_file(file_id: str) -> str:
    return f"[get-drive-file] Contents of file with id '{file_id}' (simulated)."

def main():
    user_prompt = input("Enter your prompt: ")
    system_message = (
        "You are a helpful assistant. Use the provided tools when needed to "
        "find information, verify URLs, or retrieve files. The available tools are: "
        "web-search, check-url-exists, and get-drive-file."
    )
    lg = LangGraph(system_message=system_message)
    lg.register_tool("web-search", web_search)
    lg.register_tool("check-url-exists", check_url_exists)
    lg.register_tool("get-drive-file", get_drive_file)
    result = lg.execute(user_prompt)
    print("\n--- Result ---")
    print(result)

if __name__ == "__main__":
    main()
