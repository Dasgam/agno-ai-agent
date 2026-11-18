"""Консольная точка входа: python agent/agent_cli.py."""

import asyncio
import logging
import re
import sys
from uuid import uuid4
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent import create_agent
from config import API_KEY, DATA, DEFAULT_MODEL, MODELS
from knowledge import create_knowledge, seed_knowledge
from config import DOCS
from sandbox_client import initialize_sandbox, sanitize_local_document
from openrouter_free_models import get_free_models

console = Console()
logging.basicConfig(
    filename=DATA / "agent.log",
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)

HELP = """[bold]Команды[/bold]
/help                 показать команды
/models               встроенные модели
/models-live          актуальные бесплатные модели OpenRouter
/model 9              выбрать модель по номеру
/model MODEL_ID       выбрать модель по ID
/new                  новая сессия
/session ИМЯ          открыть сессию
/id                   текущая сессия
/add ПУТЬ             безопасно добавить PDF/DOCX/TXT/MD/CSV
/docs                 загрузить файлы из agent/documents
/seed                 добавить документацию Agno
/exit                 выход
"""


def resolve_model(value: str) -> str:
    if value in MODELS:
        return MODELS[value][1]
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:free", value):
        return value
    raise ValueError("Укажи номер из /models или MODEL_ID:free")


def main() -> int:
    if not API_KEY:
        console.print("[red]В agent/.env не указан OPENROUTER_API_KEY[/red]")
        return 1
    console.print(Panel("AI Agent PRO v3.2 | Agno + OpenRouter + RAG\n/help — команды", title="Готов к работе"))
    try:
        with console.status("Открываю базу знаний CLI..."):
            knowledge = create_knowledge()
    except Exception as exc:
        logging.exception("Ошибка базы знаний")
        console.print(f"[red]Ошибка базы знаний: {exc}[/red]")
        return 1

    initialize_sandbox()
    session_id = "main"
    model_id = DEFAULT_MODEL
    agent = create_agent(knowledge, session_id, model_id)
    console.print(f"[dim]Модель: {model_id} | Сессия: {session_id}[/dim]")

    while True:
        try:
            line = Prompt.ask("\n[cyan]Вы[/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nДо встречи!")
            break
        if not line:
            continue
        command, _, arg = line.partition(" ")
        cmd = command.lower()
        arg = arg.strip()
        try:
            if cmd in ("/exit", "/quit", "выход"):
                break
            elif cmd == "/help":
                console.print(HELP)
            elif cmd == "/models":
                for number, (name, ident) in MODELS.items():
                    console.print(f"{number:>2}. {name} [dim]{ident}[/dim]")
            elif cmd == "/models-live":
                with console.status("Запрашиваю список OpenRouter..."):
                    models = get_free_models()
                console.print(f"Найдено: {len(models)}")
                for name, ident, context in models:
                    console.print(f"{name} [dim]{ident} | {context:,}[/dim]")
            elif cmd == "/model":
                new_id = resolve_model(arg)
                agent = create_agent(knowledge, session_id, new_id)
                model_id = new_id
                console.print(f"[green]Модель: {model_id}[/green]")
            elif cmd == "/new":
                new_id = uuid4().hex[:12]
                agent = create_agent(knowledge, new_id, model_id)
                session_id = new_id
                console.print(f"[green]Новая сессия: {session_id}[/green]")
            elif cmd == "/session":
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", arg):
                    console.print("[yellow]Укажи ID: латинские буквы, цифры, - или _[/yellow]")
                    continue
                agent = create_agent(knowledge, arg, model_id)
                session_id = arg
                console.print(f"[green]Сессия: {session_id}[/green]")
            elif cmd == "/id":
                console.print(f"ID: {session_id}")
            elif cmd == "/add":
                if not arg:
                    console.print("[yellow]Используй /add ПУТЬ[/yellow]")
                    continue
                with console.status("Изолированно обрабатываю и индексирую файл..."):
                    src = Path(arg.strip('"'))
                    text, pages = asyncio.run(sanitize_local_document(src))
                    knowledge.insert(text_content=text, name=src.name)
                console.print(f"[green]Добавлен: {src.name}[/green]")
            elif cmd == "/docs":
                count = 0
                with console.status("Обрабатываю документы в изоляции..."):
                    for src in sorted(DOCS.iterdir()):
                        if src.is_file() and src.suffix.lower() in ('.pdf', '.docx', '.txt', '.md', '.csv'):
                            text, pages = asyncio.run(sanitize_local_document(src))
                            knowledge.insert(text_content=text, name=src.name, skip_if_exists=True)
                            count += 1
                console.print(f"[green]Обработано: {count}[/green]")
            elif cmd == "/seed":
                with console.status("Загружаю документацию Agno..."):
                    seed_knowledge(knowledge)
                console.print("[green]Документация проиндексирована.[/green]")
            elif cmd.startswith("/"):
                console.print("[yellow]Неизвестная команда. /help[/yellow]")
            else:
                with console.status("Агент думает..."):
                    response = agent.run(line)
                answer = getattr(response, "content", None)
                console.print(
                    Panel(
                        Markdown(answer, code_theme="monokai", hyperlinks=True) if isinstance(answer, str) and answer.strip() else "Модель не вернула текст.",
                        title="Ассистент",
                        border_style="green",
                    )
                )
        except Exception as exc:
            logging.exception("Ошибка операции")
            console.print(f"[red]Ошибка: {exc}[/red]")
            console.print("[dim]Подробности: agent/data/agent.log[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
