"""Sandbox tests use a fake Docker CLI, never execute untrusted binaries."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
import sandbox_client as sc


def test_isolation_command_contains_required_restrictions(tmp_path):
    cmd = sc.docker_command("a" * 32, tmp_path / "in", tmp_path / "out", ".pdf")
    joined = " ".join(cmd)
    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--cap-drop ALL" in joined
    assert "no-new-privileges" in joined
    assert "--memory 512m" in joined
    assert "--pids-limit 64" in joined
    assert "--ulimit fsize=2097152:2097152" in joined
    assert "readonly" in joined
    assert sc.IMAGE in cmd
    assert ".pdf" == cmd[-1]
    assert "--privileged" not in cmd
    with pytest.raises(ValueError):
        sc.docker_command("../evil", tmp_path, tmp_path, ".pdf")
    with pytest.raises(ValueError):
        sc.docker_command("a" * 32, tmp_path, tmp_path, ".exe")


def test_isolated_document_only_receives_one_file(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    jobs = tmp_path / "jobs"
    inbox.mkdir()
    jobs.mkdir()
    monkeypatch.setattr(sc, "INBOX", inbox)
    monkeypatch.setattr(sc, "JOBS", jobs)
    job_id = "b" * 32
    raw = inbox / f"{job_id}.bin"
    raw.write_bytes(b"%PDF-1.7\nFAKE CONTENT, NOT PARSED IN HOST")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        assert args[0:2] == ["docker", "run"]
        # The only file mounted into the container belongs to this job.
        input_dir = jobs / job_id / "input"
        output_dir = jobs / job_id / "output"
        assert sorted(p.name for p in input_dir.iterdir()) == ["data.bin"]
        assert (input_dir / "data.bin").read_bytes() == raw.read_bytes()
        (output_dir / "content.txt").write_text("Проверенный текст. " * 12, encoding="utf-8")
        (output_dir / "result.json").write_text(
            json.dumps({"status": "ok", "pages": 2}), encoding="utf-8"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    text, pages = asyncio.run(sc.extract_isolated(job_id, raw, ".pdf"))
    assert pages == 2 and "Проверенный" in text
    assert not raw.exists() and not (jobs / job_id).exists()
    assert len(calls) == 1


def test_error_rejects_and_cleans_files(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    jobs = tmp_path / "jobs"
    inbox.mkdir()
    jobs.mkdir()
    monkeypatch.setattr(sc, "INBOX", inbox)
    monkeypatch.setattr(sc, "JOBS", jobs)
    job_id = "c" * 32
    raw = inbox / f"{job_id}.bin"
    raw.write_bytes(b"MZ" + b"A" * 200)

    def reject_run(args, **kwargs):
        output = jobs / job_id / "output"
        (output / "result.json").write_text(
            json.dumps({"status": "error", "error": "PDF имеет неверную сигнатуру"}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sc.subprocess, "run", reject_run)
    with pytest.raises(ValueError, match="сигнатуру"):
        asyncio.run(sc.extract_isolated(job_id, raw, ".pdf"))
    assert not raw.exists() and not (jobs / job_id).exists()


def test_timeout_kills_document_container(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    jobs = tmp_path / "jobs"
    inbox.mkdir()
    jobs.mkdir()
    monkeypatch.setattr(sc, "INBOX", inbox)
    monkeypatch.setattr(sc, "JOBS", jobs)
    job_id = "d" * 32
    raw = inbox / f"{job_id}.bin"
    raw.write_bytes(b"%PDF-1.7" + b"A" * 200)
    commands = []

    def timeout_run(args, **kwargs):
        commands.append(args)
        if args[1] == "run":
            raise subprocess.TimeoutExpired(args, 65)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sc.subprocess, "run", timeout_run)
    with pytest.raises(TimeoutError):
        asyncio.run(sc.extract_isolated(job_id, raw, ".pdf"))
    assert any(c[1:4] == ["rm", "-f", f"agno-sandbox-{job_id}"] for c in commands)
    assert not raw.exists() and not (jobs / job_id).exists()


def test_missing_docker_image_fails_closed(monkeypatch):
    monkeypatch.setattr(
        sc.subprocess, "run", lambda args, **kwargs: SimpleNamespace(returncode=1)
    )
    assert sc.sandbox_online() is False


def test_symlink_result_is_rejected(tmp_path):
    link = tmp_path / "unsafe.txt"
    link.symlink_to(tmp_path / "real.txt")
    with pytest.raises(ValueError, match="Небезопасный"):
        sc._safe_read(link, 50)
