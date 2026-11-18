"""One short-lived, network-disabled Docker container for each untrusted file.

The host process never imports a PDF/DOCX parser for incoming uploads.
Only one file and an empty output directory are mounted into each container.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from config import DATA

SPOOL = DATA / "sandbox_spool"
INBOX = SPOOL / "inbox"  # Host-only temporary downloads; never mounted into Docker.
JOBS = SPOOL / "jobs"
IMAGE = "agno-document-sandbox:3.2"
SUPPORTED = frozenset({".pdf", ".docx", ".txt", ".md", ".csv"})
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TEXT_BYTES = 1_200_000
MAX_RESULT_BYTES = 2_048
DOCKER_TIMEOUT = 65
ID_PATTERN = re.compile(r"[a-f0-9]{32}\Z")


def initialize_sandbox() -> None:
    """Prepare host folders and remove only abandoned temporary jobs."""
    INBOX.mkdir(parents=True, exist_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 900
    for path in INBOX.glob("*.bin"):
        if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
    for path in JOBS.iterdir():
        if path.is_dir() and not path.is_symlink() and ID_PATTERN.fullmatch(path.name):
            if path.stat().st_mtime < cutoff:
                shutil.rmtree(path)


def sandbox_online() -> bool:
    """Docker is available and the restricted parser image has been built."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _safe_read(path: Path, maximum: int) -> bytes:
    """Reject symlinks and oversized output from the untrusted container."""
    if path.is_symlink():
        raise ValueError("Небезопасный результат обработчика")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        stat = os.fstat(fd)
        if not 0 <= stat.st_size <= maximum:
            raise ValueError("Слишком большой ответ обработчика")
        content = os.read(fd, maximum + 1)
        if len(content) > maximum:
            raise ValueError("Слишком большой ответ обработчика")
        return content
    finally:
        os.close(fd)


def docker_command(job_id: str, input_dir: Path, output_dir: Path, suffix: str) -> list[str]:
    """Command is argv-only: user file names never become shell commands."""
    if not ID_PATTERN.fullmatch(job_id) or suffix not in SUPPORTED:
        raise ValueError("Некорректный запрос к изолированному обработчику")
    # Never run the document parser as root even when the host is root.
    uid = (
        f"{os.getuid()}:{os.getgid()}"
        if hasattr(os, "getuid") and os.getuid() > 0 and os.getgid() > 0
        else "1000:1000"
    )
    return [
        "docker", "run", "--rm", "--name", f"agno-sandbox-{job_id}",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--pids-limit", "64",
        "--memory", "512m", "--cpus", "1.0", "--user", uid,
        "--ulimit", "fsize=2097152:2097152", "--ulimit", "nofile=128:128",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--mount", f"type=bind,src={input_dir.resolve()},dst=/input,readonly",
        "--mount", f"type=bind,src={output_dir.resolve()},dst=/output",
        IMAGE, suffix,
    ]


def _force_remove(job_id: str) -> None:
    """Kill the container if docker run itself exceeded its timeout."""
    try:
        subprocess.run(
            ["docker", "rm", "-f", f"agno-sandbox-{job_id}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _extract_blocking(job_id: str, raw_path: Path, suffix: str) -> tuple[str, int]:
    if not ID_PATTERN.fullmatch(job_id) or suffix not in SUPPORTED:
        raise ValueError("Недопустимый файл")
    if raw_path != INBOX / f"{job_id}.bin" or raw_path.is_symlink():
        raise ValueError("Неверный путь карантина")
    size = raw_path.stat().st_size
    if not 0 < size <= MAX_FILE_BYTES:
        raise ValueError("Файл пустой или превышает 8 МБ")
    job_dir = JOBS / job_id
    in_dir = job_dir / "input"
    out_dir = job_dir / "output"
    try:
        in_dir.mkdir(parents=True, exist_ok=False)
        out_dir.mkdir(parents=True, exist_ok=False)
        # A copy prevents the container from seeing other pending uploads.
        with raw_path.open("rb") as src, (in_dir / "data.bin").open("xb") as target:
            shutil.copyfileobj(src, target, length=128 * 1024)
        cmd = docker_command(job_id, in_dir, out_dir, suffix)
        try:
            run = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=DOCKER_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            _force_remove(job_id)
            raise TimeoutError("Превышено время обработки документа") from exc
        except FileNotFoundError as exc:
            raise RuntimeError("Docker не найден. Запусти Docker Desktop") from exc
        status_path = out_dir / "result.json"
        if not status_path.is_file() and not status_path.is_symlink():
            raise RuntimeError(f"Изолированный обработчик завершился с кодом {run.returncode}")
        status = json.loads(_safe_read(status_path, MAX_RESULT_BYTES).decode("utf-8"))
        if not isinstance(status, dict) or status.get("status") != "ok":
            reason = status.get("error", "Файл отклонён") if isinstance(status, dict) else "Некорректный ответ"
            raise ValueError(str(reason)[:180])
        if run.returncode != 0:
            raise RuntimeError("Изолированный обработчик завершился с ошибкой")
        text = _safe_read(out_dir / "content.txt", MAX_TEXT_BYTES).decode("utf-8")
        pages = status.get("pages")
        if not 50 <= len(text) <= 250_000 or type(pages) is not int or not 0 <= pages <= 120:
            raise ValueError("Некорректный текст или метаданные")
        return text, pages
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        raw_path.unlink(missing_ok=True)


async def extract_isolated(job_id: str, raw_path: Path, suffix: str) -> tuple[str, int]:
    """Wait without blocking the Telegram event loop."""
    return await asyncio.to_thread(_extract_blocking, job_id, raw_path, suffix)


async def sanitize_local_document(source: Path) -> tuple[str, int]:
    """CLI follows exactly the same Docker-only path as Telegram uploads."""
    source = source.expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in SUPPORTED:
        raise ValueError("Разрешены только PDF/DOCX/TXT/MD/CSV")
    if not 0 < source.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError("Размер файла должен быть от 1 байта до 8 МБ")
    if not await asyncio.to_thread(sandbox_online):
        raise RuntimeError("Сначала собери образ: docker compose build document-sandbox")
    initialize_sandbox()
    job_id = uuid4().hex
    raw_path = INBOX / f"{job_id}.bin"
    try:
        with source.open("rb") as src, raw_path.open("xb") as dest:
            shutil.copyfileobj(src, dest, length=128 * 1024)
        return await extract_isolated(job_id, raw_path, source.suffix.lower())
    finally:
        raw_path.unlink(missing_ok=True)
