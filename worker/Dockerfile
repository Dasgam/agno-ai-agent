FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir 'pypdf>=5,<7' 'python-docx>=1.2,<2'
COPY worker/parse_once.py /app/parse_once.py
USER 1000:1000
ENTRYPOINT ["python", "-I", "/app/parse_once.py"]
