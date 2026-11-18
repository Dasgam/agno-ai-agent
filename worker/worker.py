"""Single containerized worker; launches an isolated parser subprocess per job."""
import logging
import os
import json
import re
import subprocess
import sys
import time
from pathlib import Path

INBOX = Path('/work/inbox')
OUTBOX = Path('/work/outbox')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

last_heartbeat = 0.0
while True:
    if time.time() - last_heartbeat > 2.0:
        try:
            heartbeat = OUTBOX / 'health.tmp'
            heartbeat.write_text(str(time.time()), encoding='ascii')
            os.replace(heartbeat, OUTBOX / 'health.txt')
        except OSError:
            pass
        last_heartbeat = time.time()
    for job in INBOX.glob('*.json'):
        job_id = job.stem
        if not re.fullmatch('[a-f0-9]{32}', job_id):
            continue
        if (OUTBOX / f'{job_id}.json').exists():
            continue
        try:
            finished = subprocess.run([sys.executable, '-I', '/app/parse_once.py', job_id],
                           timeout=45, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if finished.returncode and not (OUTBOX / f'{job_id}.json').exists():
                temp = OUTBOX / f'{job_id}.json.tmp'
                temp.write_text(json.dumps({'status':'error','error':'Сбой изолированного парсера'}), encoding='utf-8')
                os.replace(temp, OUTBOX / f'{job_id}.json')
        except subprocess.TimeoutExpired:
            result = OUTBOX / f'{job_id}.json'
            temp = OUTBOX / f'{job_id}.json.tmp'
            temp.write_text(json.dumps({'status':'error','error':'Превышено время обработки файла'}), encoding='utf-8')
            os.replace(temp, result)
        except OSError:
            pass
    time.sleep(0.4)
