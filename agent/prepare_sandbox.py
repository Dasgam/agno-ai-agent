"""Prepare empty shared directories before starting Docker Compose."""
from sandbox_client import initialize_sandbox, INBOX, OUTBOX

if __name__ == '__main__':
    initialize_sandbox()
    print('Sandbox directories ready:')
    print(' input:', INBOX)
    print('output:', OUTBOX)
