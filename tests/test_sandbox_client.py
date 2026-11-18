import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
import sandbox_client as sc


def test_client_only_accepts_worker_text(tmp_path, monkeypatch):
    inbox, outbox = tmp_path / 'inbox', tmp_path / 'outbox'
    inbox.mkdir()
    outbox.mkdir()
    monkeypatch.setattr(sc, 'INBOX', inbox)
    monkeypatch.setattr(sc, 'OUTBOX', outbox)
    job_id = 'a' * 32
    raw = inbox / f'{job_id}.bin'
    raw.write_bytes(b'MALICIOUS BINARY - do not parse here')

    async def fake_worker():
        for _ in range(25):
            if (inbox / f'{job_id}.json').exists():
                break
            await asyncio.sleep(0.01)
        (outbox / f'{job_id}.txt').write_text('Проверенный текст. ' * 9, encoding='utf-8')
        (outbox / f'{job_id}.json').write_text(json.dumps({'status':'ok', 'pages':2}), encoding='utf-8')

    async def run():
        worker = asyncio.create_task(fake_worker())
        data = await sc.extract_isolated(job_id, raw, '.pdf')
        await worker
        return data

    content, pages = asyncio.run(run())
    assert pages == 2
    assert 'Проверенный' in content
    assert not raw.exists()
    assert not (outbox / f'{job_id}.json').exists()


def test_health_absent_rejects_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, 'OUTBOX', tmp_path)
    assert not sc.sandbox_online()
