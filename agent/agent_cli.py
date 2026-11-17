"""CLI: python agent_cli.py"""
import logging
import sys
from uuid import uuid4
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from config import API_KEY, DEFAULT_MODEL, MODELS, DATA
from knowledge import create_knowledge, add_path, add_url, seed_knowledge, import_documents
from agent import create_agent

console = Console()
logging.basicConfig(filename=DATA / 'agent.log', level=logging.WARNING,
                    format='%(asctime)s %(levelname)s %(message)s')
HELP = '''[bold]Команды[/bold]
/help              помощь
/models            список моделей
/model НОМЕР       выбрать модель, например /model 8
/new               новая сессия
/session ID        перейти к сохранённой сессии
/id                текущая сессия
/add ПУТЬ          добавить PDF/DOCX/TXT/MD/CSV
/url HTTPS_URL     загрузить доверенный документ по ссылке
/docs              импорт файлов из папки documents
/seed              загрузить официальную документацию Agno
/exit              выход
'''


def main():
    if not API_KEY:
        console.print('[red]В .env отсутствует OPENROUTER_API_KEY[/red]')
        return 1
    console.print(Panel('AI Agent PRO • Agno + OpenRouter + RAG\n/help — команды', title='Готов к работе'))
    try:
        with console.status('Инициализация локальной базы знаний...'):
            knowledge = create_knowledge()
    except Exception as exc:
        logging.exception('Ошибка базы знаний')
        console.print(f'[red]Не удалось открыть базу знаний: {exc}[/red]')
        return 1
    session_id = 'main'
    model_id = DEFAULT_MODEL
    agent = create_agent(knowledge, session_id, model_id)
    console.print(f'[dim]Модель: {model_id} | Сессия: {session_id}[/dim]')
    while True:
        try:
            line = Prompt.ask('\n[cyan]Вы[/cyan]').strip()
        except (KeyboardInterrupt, EOFError):
            console.print('\nДо встречи!')
            break
        if not line:
            continue
        command, _, arg = line.partition(' ')
        cmd = command.lower()
        try:
            if cmd in ('/exit', '/quit', 'выход'):
                break
            elif cmd == '/help':
                console.print(HELP)
            elif cmd == '/models':
                for num, (name, ident) in MODELS.items():
                    console.print(f'{num:>2}. {name} [dim]{ident}[/dim]')
            elif cmd == '/model':
                if arg.strip() not in MODELS:
                    console.print('[yellow]Укажи номер из /models[/yellow]')
                    continue
                model_id = MODELS[arg.strip()][1]
                agent = create_agent(knowledge, session_id, model_id)
                console.print(f'[green]Модель: {model_id}[/green]')
            elif cmd == '/new':
                session_id = uuid4().hex[:12]
                agent = create_agent(knowledge, session_id, model_id)
                console.print(f'[green]Новая сессия: {session_id}[/green]')
            elif cmd == '/session':
                if not arg.strip() or len(arg.strip()) > 100 or not all(c.isalnum() or c in '-_' for c in arg.strip()):
                    console.print('[yellow]Укажи ID (буквы, цифры, - или _)[/yellow]')
                    continue
                session_id = arg.strip()
                agent = create_agent(knowledge, session_id, model_id)
                console.print(f'[green]Сессия: {session_id}[/green]')
            elif cmd == '/id':
                console.print(f'ID: [bold]{session_id}[/bold]')
            elif cmd == '/add':
                if not arg.strip():
                    console.print('[yellow]Используй /add путь_к_файлу[/yellow]')
                    continue
                with console.status('Индексирую документ...'):
                    result = add_path(knowledge, arg.strip().strip('"'))
                console.print(f'[green]Добавлен: {result}[/green]')
            elif cmd == '/url':
                if not arg.strip():
                    console.print('[yellow]Используй /url https://...[/yellow]')
                    continue
                with console.status('Загружаю источник...'):
                    result = add_url(knowledge, arg.strip())
                console.print(f'[green]Добавлен: {result}[/green]')
            elif cmd == '/seed':
                with console.status('Загружаю документацию Agno...'):
                    seed_knowledge(knowledge)
                console.print('[green]Документация Agno проиндексирована.[/green]')
            elif cmd == '/docs':
                with console.status('Индексирую documents/...'):
                    count = import_documents(knowledge)
                console.print(f'[green]Обработано файлов: {count}[/green]')
            elif cmd.startswith('/'):
                console.print('[yellow]Неизвестная команда. /help[/yellow]')
            else:
                with console.status('Думаю...'):
                    response = agent.run(line)
                answer = getattr(response, 'content', None)
                if isinstance(answer, str) and answer.strip():
                    console.print(Panel(Markdown(answer), title='Ассистент', border_style='green'))
                else:
                    console.print('[yellow]Модель не вернула текст. Попробуй другую через /model.[/yellow]')
        except Exception as exc:
            logging.exception('Ошибка операции')
            console.print(f'[red]Ошибка: {exc}[/red]')
            console.print('[dim]Подробности сохранены в data/agent.log[/dim]')
    return 0


if __name__ == '__main__':
    sys.exit(main())
