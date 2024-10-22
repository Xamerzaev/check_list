from pyrogram import Client, errors
from dotenv import load_dotenv
from os import getenv

# Загрузка переменных окружения
load_dotenv()
API_ID = getenv("API_ID")
API_HASH = getenv("API_HASH")

# Инициализация клиента Pyrogram
pyro_client = Client(
    "Myapp",
    api_id=API_ID,
    api_hash=API_HASH
)


async def send_initial_message(user_id, message_text):
    # print(f"Попытка отправить сообщение пользователю с ID: {user_id}")
    user_id = int(user_id)
    async with pyro_client as app:
        try:
            await app.send_message(chat_id=user_id, text=message_text)
            return True
        except errors.PeerIdInvalid:
            print(f"Ошибка: Неверный ID пользователя.")
            return False
        except errors.UserPrivacyRestricted:
            print(f"Ошибка: Пользователь ограничил возможность связи.")
            return False
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return False


async def add_user_to_group(user_id, group_id):
    user_id = int(user_id)
    group_id = int(group_id)
    async with pyro_client as app:
        try:
            # print(f"Попытка добавить пользователя с ID: {user_id} в группу с ID: {group_id}")
            await app.add_chat_members(chat_id=group_id, user_ids=user_id)
            return True
        except errors.PeerIdInvalid:
            print(f"Ошибка: Неверный ID пользователя или группы.")
            return False
        except errors.UserPrivacyRestricted:
            print(f"Ошибка: Пользователь ограничил возможность связи.")
            return False
        except errors.UserNotParticipant:
            print(f"Ошибка: Пользователь не участвует в чате.")
            return False
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return False