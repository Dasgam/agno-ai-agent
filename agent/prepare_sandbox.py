"""Prepare local host-only staging directories (not mounted wholesale)."""
from sandbox_client import initialize_sandbox, INBOX, JOBS

if __name__ == "__main__":
    initialize_sandbox()
    print("Sandbox directories ready:")
    print(" Downloads:", INBOX)
    print(" Isolated jobs:", JOBS)
