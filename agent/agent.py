import os, sys
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.db.sqlite import SqliteDb
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY") or sys.exit("Ошибка: в файле .env отсутствует OPENROUTER_API_KEY")
id_model = os.getenv("ID_MODEL") or sys.exit("Ошибка: в файле .env отсутствует ID_MODEL")

db = SqliteDb(db_file="data.db")
system_prompt = """
Извлекай из сообщения пользователя только сведения о нём.
Не угадывай и не выдумывай неизвестные данные.
Если сведения не указаны, оставляй соответствующее поле пустым.
""" 
# создаем строгую схему данных с помощью Pydantic
class UserProfile(BaseModel):
    name: str = Field(description="Имя пользователя")
    age: int = Field(description="Возраст пользователя в годах")
    hobbies: list[str] = Field(description="Список увлечений и хобби")
    is_student: bool = Field(description="Учится ли пользователь в данный момент (True/False)")

agent = Agent(
    model=OpenRouter(id=id_model, temperature=0.2),      
    session_id="dialog",                
    db=db,                              
    add_history_to_context=True,        
    num_history_messages=25,            # число прошлых сообщений для генерации ответа (0 - все сообщения)
    description="Ты - опытный помощник людям. Твоя задача: извлекать данные из текста и строго следовать формату.",
    instructions=system_prompt,
    output_schema=UserProfile
)


user_message = """
Привет! Меня зовут Максим, мне двадцать один год. 
Я сейчас учусь в универе на программиста. 
В свободное время обожаю кататься на сноуборде, играть в приставку и есть пиццу.
"""

# запускаем агента
print("Анализирую текст...\n")
response = agent.run(user_message)

# выводим результат. Обрати внимание: response.content - это теперь не строка, а объект UserProfile!
profile = response.content

print("Тип данных:", type(profile))
print("Имя:", profile.name)
print("Возраст:", profile.age)
print("Хобби:", profile.hobbies)
print("Студент:", profile.is_student)