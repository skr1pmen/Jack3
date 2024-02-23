import asyncio
import json
import re
import aiohttp
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from bs4 import BeautifulSoup
from app.database.base_model import Database
from app.config import DATABASE, URL, SCHEDULE, USERAGENT, ADMINS
from app.utils.group import Group
from app.utils.message import Message as message_text
from app.groups import group as group_list
from app.keyboards import main_keyboard, settings_keyboard
from aiogram.utils.markdown import hlink

user_router = Router()
db = Database(DATABASE['HOST'], DATABASE['USERNAME'], DATABASE['PASSWORD'], DATABASE['BASENAME'])


@user_router.message(CommandStart())
async def start_cmd(msg: Message, state: FSMContext):
    user_exists = db.fetch("""SELECT id FROM users WHERE chat_id = %s""", msg.chat.id)
    if not user_exists:
        welcome_message = (f"Привет, {msg.from_user.first_name}! Я Джек, помощник в отслеживании изменений в "
                           f"расписании.\nЕсли ты хочешь, чтобы я отправлял тебе расписание твоей группы,то укажи, "
                           f"пожалуйста, для начала её название.\n<i>Пример: МК-22</i>")
        sticker_hi = 'CAACAgIAAxkBAAEFxFRjFnKx2k7rTEcWbXsJu0z5xlTMUwACiBEAArOMcUnCJQLlwkLsoikE'

        await state.set_state(Group.group)
        await msg.answer_sticker(sticker_hi)
        await msg.answer(welcome_message)
    else:
        code = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
        await msg.answer(f"Привет, {msg.from_user.first_name}! Ты уже зарегистрирован у меня. "
                         f"Повторно вводить команду не нужно!", reply_markup=main_keyboard.main(URL+str(code)))


@user_router.message(Group.group)
async def set_group_cmd(msg: Message, state: FSMContext):
    await state.update_data(group=msg.text)
    data = await state.get_data()
    await state.clear()
    for name, code in group_list.items():
        if name == data['group'].lower():
            if bool(db.fetch("""SELECT COUNT(*) FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]) is False:
                db.execute(
                    """INSERT INTO users (name, surname, username, class, chat_id) VALUES (%s, %s, %s, %s, %s)""",
                    msg.from_user.first_name, msg.from_user.last_name, msg.from_user.username, code, msg.chat.id
                )
            else:
                db.execute("""UPDATE users SET class = %s WHERE chat_id = %s""", code, msg.chat.id)
            await msg.answer(
                "Хорошо, теперь ты будешь получать расписание этой группы.",
                reply_markup=main_keyboard.main(f"{URL}{code}"))
            break
        continue
    else:
        await state.set_state(Group.group)
        await msg.answer("Прости, но я не знаю такую группу. Попробуй ввести ещё раз!")


@user_router.message(F.text.lower() == "сбросить базу расписаний ⭕")
@user_router.message(Command('db_reset'))
async def db_reset_cmd(msg: Message):
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    if msg.chat.id in ADMINS:
        db.execute("""TRUNCATE schedules""")
        [db.execute(
            """INSERT INTO schedules (class) VALUES (%s)""", code)
            for _, code in group_list.items()]
        await msg.answer("Успешно❕\nБаза расписания была сброшена!", reply_markup=main_keyboard.main(URL+str(user_class)))
    else:
        await msg.answer("Ошибка❗\nТебе недоступна данная команда!", reply_markup=main_keyboard.main(URL+str(user_class)))


@user_router.message(Command('update_schedule'))
async def get_new_schedule(bot: Bot):
    # Overwriting the old schedule for future comparison with the new one
    old_schedule = [db.fetch(
        """SELECT schedule FROM schedules WHERE class = %s""", code)[0][0]
                    for _, code in group_list.items()]

    # Obtaining new data from the college website
    aiohttp_client = aiohttp.ClientSession()
    try:
        tasks = [aiohttp_client.get(f"{URL}{code}", headers=USERAGENT) for name, code in group_list.items()]
        tasks_finish = await asyncio.gather(*tasks)
        codes = [code for _, code in group_list.items()]
        for task_item, task in enumerate(tasks_finish):
            if task.status == 200:
                schedule = await task.text()
                soup = BeautifulSoup(schedule, "html.parser")

                i = 1
                for number in soup.find_all('td', class_="thead"):
                    finish = re.sub(r'[|—\n]', '', number.get_text())
                    if i == 1:
                        SCHEDULE['today']['day'] = finish.strip()
                    elif i == 9:
                        SCHEDULE['tomorrow']['day'] = finish.strip()
                    i += 1

                i = 1
                for item in soup.find_all('td', class_="td-bold"):
                    finish = re.sub(r'[|—\n]', '', item.get_text())

                    if i <= 7:
                        if finish.strip() == "":
                            SCHEDULE['today'][i] = "Нет пары."
                        else:
                            SCHEDULE['today'][i] = finish.strip()
                    else:
                        if finish.strip() == "":
                            SCHEDULE['tomorrow'][i - 7] = "Нет пары"
                        else:
                            SCHEDULE['tomorrow'][i - 7] = finish.strip()
                    i += 1

                async def schedule_comparison(old_schedule, new_schedule):
                    if old_schedule is not None:
                        new = []
                        old = []

                        for _, value_old in old_schedule.items():
                            old.append(value_old['day'])
                            for i in range(1, 8):
                                old.append(value_old[f'{i}'])
                        for _, value_new in new_schedule.items():
                            new.append(value_new['day'])
                            for i in range(1, 8):
                                new.append(value_new[i])

                        return old == new
                    else:
                        return False

                comparison = await schedule_comparison(old_schedule[task_item], SCHEDULE)
                if not comparison:
                    schedule_json = json.dumps(SCHEDULE, ensure_ascii=False)

                    db.execute("""UPDATE schedules SET schedule = %s WHERE class = %s""", schedule_json,
                               codes[task_item])
                    chats_id = db.fetch("""SELECT chat_id FROM users WHERE class = %s""", codes[task_item])
                    if chats_id is not None:
                        for chat_id in chats_id:
                            schedule = json.loads(schedule_json)
                            message = await schedule_converter(schedule)
                            try:
                                await bot.send_message(int(chat_id[0]), f"На сайте обновили расписание:\n\n{message}")
                            except Exception as e:
                                db.fetch("""DELETE FROM users WHERE chat_id = %s""", int(chat_id[0]))
            else:
                raise Exception(f"Сайт не дал ответ для группы {task.url}")
    except Exception as e:
        print(e)
    finally:
        await aiohttp_client.close()


async def schedule_converter(schedule):
    message = f"<b>{schedule['today']['day']}</b>\n"
    lessons = schedule['today']
    i = 1
    while i <= 7:
        message += f"<b>{i}: </b>" + lessons[f'{i}'] + "\n"
        if i != 7:
            i += 1
        else:
            break
    message += f"<b>{schedule['tomorrow']['day']}</b>\n"
    lessons = schedule['tomorrow']
    i = 1
    while i <= 7:
        message += f"<b>{i}: </b>" + lessons[f'{i}'] + "\n"
        if i != 7:
            i += 1
        else:
            break
    return message


@user_router.message(F.text.lower() == "расписание 📅")
async def get_schedule_cmd(msg: Message):
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    class_schedule = db.fetch(
        """SELECT schedule FROM schedules WHERE class = %s""",
        user_class
    )[0][0]
    await msg.answer(f"Расписание занятий на данный момент:\n\n{await schedule_converter(class_schedule)}")


@user_router.message(F.text.lower() == "звонки 🔔")
async def get_bell_cmd(msg: Message):
    with open("./app/bell.json", encoding="utf-8") as bell:
        bell = json.load(bell)
        bell_text: str = "Расписание звонков:\n"
        for day in bell:
            bell_text += f"\n<b>{day}</b>:\n"
            for line in bell[f"{day}"]:
                bell_text += f"<b>{line}</b>: {bell[day][line]}\n"
    await msg.answer(bell_text)


@user_router.message(F.text.lower() == "помощь 📞")
async def get_help_cmd(msg: Message):
    await msg.answer("В случае возникновения каких либо вопросов/ошибок обращайтесь к @skr1pmen. "
                     "В начале сообщения указал #JackBot")


@user_router.message(F.text.lower() == "настройки ⚙")
async def get_settings_cmd(msg: Message):
    if msg.chat.id in ADMINS:
        if db.fetch("""SELECT mailing FROM bot_settings""")[0][0]:
            await msg.answer(f"Доступные настройки:",
                             reply_markup=settings_keyboard.settings())
        else:
            await msg.answer(f"Доступные настройки:",
                             reply_markup=settings_keyboard.settings(False))
    else:
        await msg.answer(f"Доступные настройки:",
                         reply_markup=settings_keyboard.user_settings())


@user_router.message(F.text.lower() == "назад ◀")
async def back_cmd(msg: Message):
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    await msg.answer("Возвращаю в меню", reply_markup=main_keyboard.main(URL+str(user_class)))


@user_router.message(F.text.lower() == "изменить группу 📔")
async def edit_group_cmd(msg: Message, state: FSMContext):
    db.execute("""UPDATE users SET class = 0 WHERE chat_id = %s""", msg.chat.id)
    await state.set_state(Group.group)
    await msg.answer("Введи, пожалуйста, название группы, чтобы её изменить.\n<i>Пример: МК-22</i>")


@user_router.message(F.text.lower() == "отключить рассылку 📮")
@user_router.message(F.text.lower() == "включить рассылку 📮")
async def switching_mailing_cmd(msg: Message):
    db.execute("""UPDATE bot_settings SET mailing = not mailing""")
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    await msg.answer("Успешно❕\nНастройки были изменены.", reply_markup=main_keyboard.main(URL+str(user_class)))


@user_router.message(F.text.lower() == "рассылка сообщения 💬")
async def message_distribution_cmd(msg: Message, state: FSMContext):
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    if msg.chat.id in ADMINS:
        await state.set_state(message_text.message)
        await msg.answer("Введите сообщения для рассылки.\n<i>Шаблоны:\n{name} - имя пользователя\n"
                     "{my} - @skr1pmen\n{bot} - Ссылка на бота</i>",
                         reply_markup=main_keyboard.main(URL + str(user_class)))
    else:
        await msg.answer("Ошибка❗\nТебе недоступна данная команда!",
                         reply_markup=main_keyboard.main(URL + str(user_class)))


@user_router.message(message_text.message)
async def set_message_cmd(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data(message=msg.text)
    data = await state.get_data()
    await state.clear()
    await msg.answer("Успешно❕\nСообщение начинает рассылаться.")
    data = data["message"]
    all_users = db.fetch("""SELECT chat_id, name FROM users""")
    for user in all_users: # user[0] -> id, user[1] -> user name
        try:
            if user[0] == msg.chat.id:
                continue
            await bot.send_message(
                user[0],
                data.replace("{name}", user[1]).replace("{my}", "@skr1pmen").replace("{bot}", hlink("Jack", "https://t.me/srmk_bot?start=1"))
            )
        except Exception as e:
            db.execute("""DELETE FROM users WHERE chat_id = %s""", user[0])


@user_router.message()
async def user_cmd(msg: Message):
    await msg.answer("Прости, но я тебя не понимаю 😞")
