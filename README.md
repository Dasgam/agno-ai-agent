
# 🤖 Agno AI Agent — v2.0

Интеллектуальный AI-ассистент на Python, созданный с использованием Agno и OpenRouter.

Проект объединяет языковые модели, интернет-поиск, локальную память, векторную базу знаний и финансовые инструменты.

## 🚀 Возможности

- Поддержка бесплатных моделей OpenRouter
- Переключение моделей через CLI
- Получение актуального списка моделей
- Резервные модели при сбоях основного маршрута
- Сохранение истории диалогов в SQLite
- RAG на базе LanceDB
- Многоязычные эмбеддинги SentenceTransformers
- Интернет-поиск через WebSearchTools
- Финансовые данные Yahoo Finance
- Загрузка PDF, DOCX, TXT, MD и CSV
- Логирование и обработка ошибок

## 🛠 Технологии

Python 3.12 · Agno · OpenRouter · SQLite · LanceDB · SentenceTransformers · Rich · Yahoo Finance

## 📂 Структура проекта

```text
agno-ai-agent/
├── agent/
│   ├── agent.py
│   ├── agent_cli.py
│   ├── config.py
│   ├── knowledge.py
│   ├── openrouter_free_models.py
│   └── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 📦 Установка

Клонирование репозитория:

```bash
git clone https://github.com/Dasgam/agno-ai-agent.git
cd agno-ai-agent
```

Создание виртуального окружения:

```bash
py -3.12 -m venv .venv
```

Активация в Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

Установка зависимостей:

```bash
python -m pip install -r requirements.txt
```

## ⚙️ Настройка

Скопируйте `agent/.env.example` в `agent/.env`.

Укажите API-ключ OpenRouter:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
ID_MODEL=nvidia/nemotron-3.5-lightning:free
```

Получить ключ можно на https://openrouter.ai/

## ▶️ Запуск

```bash
python agent/agent_cli.py
```

## 💻 Команды CLI

| Команда | Описание |
|---|---|
| `/help` | Список команд |
| `/models` | Сохранённый список моделей |
| `/models-live` | Актуальные бесплатные модели |
| `/model 8` | Выбор модели по номеру |
| `/model MODEL_ID` | Выбор модели по ID |
| `/new` | Новая сессия |
| `/session ID` | Открыть сохранённую сессию |
| `/id` | Показать ID текущей сессии |
| `/add ПУТЬ` | Загрузить документ |
| `/url HTTPS_URL` | Загрузить доверенный источник |
| `/docs` | Импортировать документы из папки |
| `/seed` | Загрузить документацию Agno |
| `/exit` | Завершить работу |

## 🧠 RAG

Ассистент использует локальную векторную базу LanceDB и многоязычные эмбеддинги.

Для загрузки официальной документации Agno:

```text
/seed
```

Для добавления собственного документа:

```text
/add C:\Documents\manual.pdf
```

Данные сохраняются локально и не добавляются в Git.

## 🔐 Безопасность

API-ключ хранится в `.env`, который исключён из Git.

Не публикуйте реальные ключи API и личные документы.

## 🗺 Roadmap

- [x] Консольный AI-агент
- [x] Поддержка нескольких моделей
- [x] Хранение истории
- [x] RAG с LanceDB
- [x] Интернет-поиск
- [ ] Telegram-бот
- [ ] Автоматический выбор модели
- [ ] Расширенная долговременная память
- [ ] Веб-интерфейс

## 📄 Лицензия

Лицензия пока не указана.

---

**Автор:** [Dasgam](https://github.com/Dasgam)
