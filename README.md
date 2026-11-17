# 🤖 AI Agent PRO

Интеллектуальный AI-ассистент на Python с использованием Agno и OpenRouter.

## 🚀 Возможности

- Поддержка 14 бесплатных AI-моделей через OpenRouter
- Переключение моделей прямо в терминале
- Сохранение истории диалогов в SQLite
- RAG-система с LanceDB для поиска по документам
- Поиск информации в интернете
- Работа с PDF, DOCX, TXT и Markdown
- Финансовые инструменты Yahoo Finance
- Интерактивный консольный интерфейс

## 🛠 Технологии

- Python 3.11–3.12
- Agno
- OpenRouter
- SQLite
- LanceDB
- SentenceTransformers
- DuckDuckGo

## 📦 Установка

Клонируйте репозиторий:

```bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
```

Создайте виртуальное окружение:

```bash
python -m venv .venv
```

Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

Создайте файл `agent/.env` и добавьте:

```env
OPENROUTER_API_KEY=your_api_key
ID_MODEL=nvidia/nemotron-3.5-lightning:free
```

## ▶️ Запуск

```bash
python agent/agent_cli.py
```

## 💻 Команды

| Команда | Описание |
|---|---|
| `/help` | Список команд |
| `/models` | Доступные модели |
| `/model 8` | Выбрать модель |
| `/new` | Создать новую сессию |
| `/seed` | Загрузить базу знаний |
| `/docs` | Просмотр документов |
| `/exit` | Завершить работу |

## 🔐 Безопасность

API-ключи хранятся локально в `.env`, который не должен попадать в GitHub.

## 📌 Статус

Проект находится в разработке. Планируется добавление Telegram-бота, автоматического выбора моделей и расширенной долговременной памяти.
