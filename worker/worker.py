"""Retired in v3.2: each document now runs in a fresh Docker container.

Kept as a harmless compatibility placeholder for old project checkouts.
"""

if __name__ == "__main__":
    raise SystemExit("Use: docker compose build document-sandbox; then run the Telegram bot")
