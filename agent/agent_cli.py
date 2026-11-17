
"""Консольный интерфейс AI Agent PRO."""

import logging
import sys
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from config import API_KEY, DEFAULT_MODEL, MODELS, DATA
from knowledge import (
    create_knowledge,
    add_path,
    add_url,
    seed_knowledge,
    import_documents,
)
from agent import create_agent
from openrouter_free_models import get_free_models


console = Console()

logging.basicConfig(
    filename=DATA / "agent.log",
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)

HELP = """
[bold cyan]Команды AI Agent PRO[/bold cyan]

[bold]Модели:[/bold]
/models            Сохранённый список моделей
/models-live       Актуальные бесплатные модели OpenRouter
/model НОМЕР       Выбрать модель по номеру
/model MODEL_ID    Выбрать модель по полному ID

[bold]Сессии:[/bold]
/new               Создать новую сессию
/session ID        Открыть сохранённую сессию
/id                Показать текущую сессию

[bold]База знаний:[/bold]
/add ПУТЬ          Добавить PDF/DOCX/TXT/MD/CSV
/url HTTPS_URL     Добавить документ по ссылке
/docs              Импортировать файлы из documents/
/seed              Загрузить документацию Agno

[bold]Прочее:[/bold]
/help              Показать команды
/exit              Завершить работу
"""


def show_models():
    """Показать сохранённый список моделей."""

    console.print(
        "\n[bold cyan]Доступные модели:[/bold cyan]\n"
    )

    for number, (name, model_id) in MODELS.items():
        console.print(
            f"[bold green]{number:>2}.[/bold green] "
            f"{name}\n"
            f"    [dim]{model_id}[/dim]"
        )


def show_live_models():
    """Получить актуальные бесплатные модели OpenRouter."""

    with console.status(
        "[cyan]Получаю модели OpenRouter...[/cyan]"
    ):
        models = get_free_models()

    if not models:
        console.print(
            "[yellow]Бесплатные модели не найдены.[/yellow]"
        )
        return

    console.print(
        f"\n[bold green]Найдено моделей: "
        f"{len(models)}[/bold green]\n"
    )

    for number, (name, model_id, context) in enumerate(
        models, start=1
    ):
        console.print(
            f"[bold cyan]{number:>2}.[/bold cyan] "
            f"{name}\n"
            f"    [dim]ID: {model_id}[/dim]\n"
            f"    [dim]Контекст: {context:,}[/dim]"
        )

    console.print(
        "\n[dim]Для выбора модели используй "
        "/model MODEL_ID[/dim]"
    )


def resolve_model(value):
    """Определить ID модели по номеру или строке."""

    value = value.strip()

    if not value:
        raise ValueError(
            "Укажи номер модели или полный MODEL_ID."
        )

    if value in MODELS:
        return MODELS[value][1]

    if (
        "/" in value
        and value.endswith(":free")
        and not any(char.isspace() for char in value)
    ):
        return value

    raise ValueError(
        "Некорректная модель. "
        "Используй /models или /models-live."
    )


def show_answer(response):
    """Отобразить ответ модели."""

    answer = getattr(response, "content", None)

    if isinstance(answer, str) and answer.strip():
        console.print(
            Panel(
                Markdown(answer),
                title="[bold green]Ассистент[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )
    elif answer is not None:
        console.print(
            Panel(
                str(answer),
                title="Ассистент",
                border_style="green",
            )
        )
    else:
        console.print(
            "[yellow]Модель не вернула текст. "
            "Попробуй другую через /model.[/yellow]"
        )


def main():
    """Основной цикл приложения."""

    if not API_KEY:
        console.print(
            "[bold red]Ошибка:[/bold red] "
            "В .env отсутствует OPENROUTER_API_KEY"
        )
        return 1

    console.print(
        Panel(
            "[bold cyan]AI Agent PRO v2.0[/bold cyan]\n"
            "[white]Agno + OpenRouter + RAG[/white]\n\n"
            "[dim]/help — список команд[/dim]",
            title="[bold green]Агент готов[/bold green]",
            border_style="cyan",
        )
    )

    try:
        with console.status(
            "[cyan]Инициализация базы знаний...[/cyan]"
        ):
            knowledge = create_knowledge()

    except Exception as exc:
        logging.exception("Ошибка базы знаний")

        console.print(
            f"[red]Не удалось открыть базу знаний: "
            f"{exc}[/red]"
        )
        return 1

    session_id = "main"
    model_id = DEFAULT_MODEL

    try:
        agent = create_agent(
            knowledge,
            session_id,
            model_id,
        )

    except Exception as exc:
        logging.exception("Ошибка создания агента")
        console.print(
            f"[red]Не удалось создать агента: "
            f"{exc}[/red]"
        )
        return 1

    console.print(
        f"\n[green]Модель:[/green] {model_id}\n"
        f"[green]Сессия:[/green] {session_id}"
    )

    while True:
        try:
            line = Prompt.ask(
                "\n[bold cyan]Вы[/bold cyan]"
            ).strip()

        except (KeyboardInterrupt, EOFError):
            console.print(
                "\n[cyan]До встречи![/cyan]"
            )
            break

        if not line:
            continue

        command, _, arg = line.partition(" ")
        cmd = command.lower()
        arg = arg.strip()

        try:

            if cmd in ("/exit", "/quit", "выход"):
                console.print(
                    "[cyan]Завершение работы агента.[/cyan]"
                )
                break

            elif cmd == "/help":
                console.print(HELP)

            elif cmd == "/models":
                show_models()

            elif cmd == "/models-live":
                show_live_models()

            elif cmd == "/model":
                try:
                    new_model_id = resolve_model(arg)

                    new_agent = create_agent(
                        knowledge,
                        session_id,
                        new_model_id,
                    )

                    agent = new_agent
                    model_id = new_model_id

                    console.print(
                        f"[bold green]Модель выбрана:"
                        f"[/bold green] {model_id}"
                    )

                except ValueError as exc:
                    console.print(
                        f"[yellow]{exc}[/yellow]"
                    )

            elif cmd == "/new":
                new_session_id = uuid4().hex[:12]

                agent = create_agent(
                    knowledge,
                    new_session_id,
                    model_id,
                )

                session_id = new_session_id

                console.print(
                    f"[green]Новая сессия: "
                    f"{session_id}[/green]"
                )

            elif cmd == "/session":
                if (
                    not arg
                    or len(arg) > 100
                    or not all(
                        c.isalnum() or c in "-_"
                        for c in arg
                    )
                ):
                    console.print(
                        "[yellow]Укажи ID сессии: "
                        "буквы, цифры, - или _[/yellow]"
                    )
                    continue

                new_agent = create_agent(
                    knowledge,
                    arg,
                    model_id,
                )

                agent = new_agent
                session_id = arg

                console.print(
                    f"[green]Сессия: "
                    f"{session_id}[/green]"
                )

            elif cmd == "/id":
                console.print(
                    f"[cyan]Текущая сессия:[/cyan] "
                    f"[bold]{session_id}[/bold]"
                )

            elif cmd == "/add":
                if not arg:
                    console.print(
                        "[yellow]Используй: "
                        "/add путь_к_файлу[/yellow]"
                    )
                    continue

                with console.status(
                    "[cyan]Индексирую документ...[/cyan]"
                ):
                    result = add_path(
                        knowledge,
                        arg.strip('"'),
                    )

                console.print(
                    f"[green]Документ добавлен: "
                    f"{result}[/green]"
                )

            elif cmd == "/url":
                if not arg:
                    console.print(
                        "[yellow]Используй: "
                        "/url https://...[/yellow]"
                    )
                    continue

                with console.status(
                    "[cyan]Загружаю источник...[/cyan]"
                ):
                    result = add_url(
                        knowledge,
                        arg,
                    )

                console.print(
                    f"[green]Источник добавлен: "
                    f"{result}[/green]"
                )

            elif cmd == "/seed":
                with console.status(
                    "[cyan]Загружаю документацию "
                    "Agno...[/cyan]"
                ):
                    seed_knowledge(knowledge)

                console.print(
                    "[green]Документация Agno "
                    "проиндексирована.[/green]"
                )

            elif cmd == "/docs":
                with console.status(
                    "[cyan]Индексирую документы...[/cyan]"
                ):
                    count = import_documents(
                        knowledge
                    )

                console.print(
                    f"[green]Обработано файлов: "
                    f"{count}[/green]"
                )

            elif cmd.startswith("/"):
                console.print(
                    "[yellow]Неизвестная команда. "
                    "Используй /help[/yellow]"
                )

            else:
                with console.status(
                    "[cyan]Агент думает...[/cyan]"
                ):
                    response = agent.run(line)

                show_answer(response)

        except Exception as exc:
            logging.exception(
                "Ошибка выполнения операции"
            )

            console.print(
                f"[bold red]Ошибка:[/bold red] "
                f"{exc}"
            )

            console.print(
                "[dim]Подробности записаны "
                "в data/agent.log[/dim]"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
