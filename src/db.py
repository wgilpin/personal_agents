import os
from tinydb import TinyDB, Query


class Database:
    def __init__(self):
        """Initializes the TinyDB database for workflows."""
        db_path = os.path.join(os.path.dirname(__file__), "db", "workflows.json")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure 'db' directory exists
        self.db = TinyDB(db_path)
        self.workflows_table = self.db.table("workflows")
        self.workflow_query = Query()
