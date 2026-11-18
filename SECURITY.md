# Security policy — Agno AI Agent v3.2

This is an educational/personal project, not a certified malware-analysis platform.

## Threat model

- A Telegram user on the allowlist may upload a hostile PDF, DOCX or plain-text document.
- The host Telegram process **must never parse uploaded binary documents directly**.
- Each upload is first placed into a random host-only quarantine path, then copied into a **one-file-per-container** input directory.
- A short-lived Docker container with no network, readonly filesystem, nonroot user, no capabilities and resource limits extracts plaintext.
- Only the plaintext and document metadata are returned; raw files and temporary per-job directories are deleted.
- The bot passes document text as untrusted data to a tool-free, **non-persistent** agent in document mode; extracted text is not saved in the regular Agno chat-history SQLite database. Other messages can still use web tools.

## Remaining risks

1. The Docker engine and host operating system are trusted. Container isolation is **not a VM boundary** and may contain vulnerabilities.
2. There is **no antivirus scanner**. Signature checks and structural validation do not detect all malware.
3. Host quarantine temporarily stores untrusted files. The extracted text and vector index persist in local storage until deletion or retention expiration.
4. Deleted LanceDB records may remain in snapshots, old versions, filesystem backups or SSD blocks. This is logical removal, not forensic secure erasure.
5. Document text can attempt prompt injection. In document mode the agent has no tools, but output text may still be manipulated.
6. OpenRouter receives questions and selected excerpts for inference. Do not upload confidential material without permission.
7. Secrets and logs need filesystem-level access control. Consider full-disk encryption, backups, and patch management.
8. Resource quotas are per Telegram account and do not protect against every denial-of-service scenario.

## Setup requirements

- Never commit `agent/.env`, API keys or bot tokens.
- Revoke and regenerate any leaked Telegram bot tokens via BotFather.
- Keep Docker Desktop, Python, Agno, python-telegram-bot and parsing libraries updated.
- Run with a trusted Docker engine. Do not mount `/var/run/docker.sock` into an untrusted container.
- Limit `TELEGRAM_OWNER_ID` to trusted accounts.
- Review access to `agent/data/` if the host is shared.
- Check Docker output and Python logs without publishing secret URLs.

## Reporting

Report vulnerabilities privately to the repository maintainer via GitHub's private vulnerability reporting if it is enabled; otherwise ask the maintainer for a private contact method. Do not post tokens, malicious document payloads or private data in public issues.

## Upgrade note from v3.1

Prior versions could persist retrieved document snippets in `agent/data/sessions.sqlite3` as user-message history. Version 3.2 does not retain new document context in that database, but **does not retroactively purge old history**. To remove previous snippets, stop all agent processes and remove the old session database (including WAL/SHM files) after creating a backup. This resets chat history; backups and filesystem snapshots also require separate handling.
