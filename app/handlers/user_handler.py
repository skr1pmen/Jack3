import asyncio
import json
import re
import aiohttp
import sys
import websockets

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from bs4 import BeautifulSoup
from app.database.base_model import Database
from app.config import DATABASE, URL, SCHEDULE, USERAGENT, ADMINS
from app.utils.group import Group, AddGroup
from app.utils.suggestion import Suggestion
from app.utils.message import Message as message_text
from app.groups import group as group_list
from app.keyboards import main_keyboard, settings_keyboard, not_group_keyboard, additional_classes_kb
from aiogram.utils.markdown import hlink
from datetime import datetime
from app import config
from app.utils.utils import *

user_router = Router()
db = Database(DATABASE['HOST'], DATABASE['USERNAME'], DATABASE['PASSWORD'], DATABASE['BASENAME'])

# db.execute("""insert into logs (type, message) values ('info', %s)""", "Bot started (tested)" if '--test-start' in sys.argv else "Bot started")

@user_router.message(CommandStart())
async def start_cmd(msg: Message, state: FSMContext):
    user_exists = db.fetch("""SELECT id FROM users WHERE chat_id = %s""", msg.chat.id)
    if not user_exists:
        welcome_message = (f"Привет, {msg.from_user.first_name}! Я Джек, помощник в отслеживании изменений в "
                           f"расписании.\nЕсли ты хочешь, чтобы я отправлял тебе расписание твоей группы,то укажи, "
                           f"пожалуйста, для начала её название.\n<i>Пример: МК-22</i>"
                           f"\n\n⚠Внимание!⚠ Бот не будет работать в групповых чатах, "
                           f"он предназначен только для личных сообщений")
        sticker_hi = 'CAACAgIAAxkBAAEFxFRjFnKx2k7rTEcWbXsJu0z5xlTMUwACiBEAArOMcUnCJQLlwkLsoikE'

        await state.set_state(Group.group)
        await msg.answer_sticker(sticker_hi)
        await msg.answer(welcome_message, reply_markup=not_group_keyboard.main())
        db.execute(f"""insert into logs (type, message) values ('info', 'The user with id {msg.from_user.id} has joined the bot')""")
    else:
        code = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
        await msg.answer(f"Привет, {msg.from_user.first_name}! Ты уже зарегистрирован у меня. "
                         f"Повторно вводить команду не нужно!", reply_markup=main_keyboard.main(URL + str(code)))
        db.execute(f"""insert into logs (type, message) values ('info', 'User with id {msg.chat.id} tried to re-register')""")


@user_router.message(F.text.lower() == "я пока не студент колледжа 🎓")
async def get_schedule_cmd(msg: Message):
    await msg.answer(
        "К сожалению я не могу помочь тебе ничем кроме как дать контакты колледжа. Я надеюсь это тебе поможет 👍\n\n"
        "<b>Информация о месте нахождения образовательной организации:</b>\n"
        "юридический адрес: 355044, Ставропольский край, г. Ставрополь, пр. Юности, д. 3\n"
        "фактический адрес: 355044, Ставропольский край, г. Ставрополь, пр. Юности, д. 3\n\n"
        "<b>Информация о режиме и графике работы образовательной организации:</b>\n"
        "<b>Режим проведения учебных занятий:</b> В соответствии с расписанием учебных занятий в период с 8.00 до 20.00\n\n"
        "<b>График работы структурных подразделений ГБПОУ СРМК:</b>\n"
        "<b>Общий</b>: понедельник – пятница с 8.00 до 17.00; перерыв с 12.00 до 13.00\n"
        "<b>Читальный зал</b>: понедельник - пятница с 8.00 до 17.00\n"
        "<b>Абонементы библиотеки</b>: понедельник-пятница с 8.00 до 17.00\n\n"
        "<b>Информация о контактных телефонах образовательной организации:</b>\n"
        "Контактный телефон и факс: 8-(8652)-39-21-10\n\n"
        "<b>Информация об адресах электронной почты образовательной организации:</b>\n"
        "Адрес электронной почты образовательной организации: srmk@mosk.stavregion.ru"
    )

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
                db.execute("""UPDATE statistics SET added = added + 1""")
                db.execute(
                    f"""insert into logs (type, message) values ('info', 'The user with id {msg.from_user.id} has completed registration and is now receiving a schedule')""")
            else:
                db.execute("""UPDATE users SET class = %s WHERE chat_id = %s""", code, msg.chat.id)
                db.execute(
                    f"""insert into logs (type, message) values ('info', 'The user with id {msg.from_user.id} has changed his group')""")
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
        await msg.answer("Успешно❕\nБаза расписания была сброшена!",
                         reply_markup=main_keyboard.main(URL + str(user_class)))
        db.execute(f"""insert into logs (type, message) values ('info', 'All band schedules have been reset')""")
    else:
        await msg.answer("Ошибка❗\nТебе недоступна данная команда!",
                         reply_markup=main_keyboard.main(URL + str(user_class)))
        db.execute(f"""insert into logs (type, message) values ('warning', 'User {msg.chat.id} attempted to reset the group schedule')""")


@user_router.message(Command('get_statistics'))
async def get_statistics(bot: Bot):
    statistics = db.fetch("""SELECT * FROM statistics""")[0]
    db.execute("""UPDATE statistics SET added = 0, delete = 0""")
    db.execute(
        """INSERT INTO statistics_history (week, year, added, deleted) VALUES (%s, %s, %s, %s)""",
        datetime.now().isocalendar().week - 1,
        datetime.now().isocalendar().year,
        statistics[0],
        statistics[1]
    )
    db.execute(f"""insert into logs (type, message) values ('info', 'The statistics for the week have been updated')""")
    await bot.send_message(ADMINS[0],
                           f"Статистика за неделю:\n+{statistics[0]} пользователей🎉🎉🎉\n"
                           f"Удалено пользователей: {statistics[1]}!")


@user_router.message(Command('update_schedule'))
async def get_new_schedule(bot: Bot):
    if not db.fetch("""SELECT mailing FROM bot_settings""")[0][0]:
        return
    # Overwriting the old schedule for future comparison with the new one
    old_schedule = [db.fetch(
        """SELECT schedule FROM schedules WHERE class = %s""", code)[0][0]
                    for _, code in group_list.items()]

    # Obtaining new data from the college website
    aiohttp_client = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
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
                            SCHEDULE['today'][i] = "Нет пары"
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
                    chats_id = db.fetch("""SELECT chat_id FROM users WHERE class = %s OR %s = ANY(additional_classes)""", codes[task_item], codes[task_item])
                    if chats_id is not None:
                        for chat_id in chats_id:
                            schedule = json.loads(schedule_json)
                            message = await schedule_converter(schedule)
                            try:
                                await bot.send_message(
                                    int(chat_id[0]),
                                    f"На сайте обновили расписание:\n\n{message}",
                                    reply_markup=main_keyboard.main(URL + str(codes[task_item])))
                            except Exception as e:
                                db.execute("""DELETE FROM users WHERE chat_id = %s""", int(chat_id[0]))
                                db.execute("""UPDATE statistics SET delete = delete + 1""")
                                db.execute(f"""insert into logs (type, message) values ('error', '{e}')""")
            else:
                db.execute(f"""insert into logs (type, message) values ('error', 'The site did not provide a response for the {task.url} group')""")
                raise Exception(f"Сайт не дал ответ для группы {task.url}")
    except Exception as e:
        print(e)
        db.execute("""insert into logs (type, message) values ('error', %s)""", e)
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
async def get_schedule_cmd(msg: Message, state: FSMContext):
    user_class = db.fetch("""SELECT class, additional_classes FROM users WHERE chat_id = %s""", msg.chat.id)[0]

    async def error_def():
        await msg.answer(
            f"Прости, но у тебя не указана группа! Давай сделаем это сейчас.\n"
            f"Введи, пожалуйста, название группы.\n<i>Пример: МК-22</i>")
        await state.set_state(Group.group)

    try:
        if user_class[0] != 0:
            class_schedule = db.fetch(
                """SELECT schedule FROM schedules WHERE class = %s""",
                user_class[0]
            )[0][0]
            if not class_schedule:
                await msg.answer(f"Расписание пока недоступно!")
                return
            await msg.answer(f"Расписание занятий для группы <b>{(await get_group_name_by_class_code(user_class[0])).upper()}</b>:\n\n{await schedule_converter(class_schedule)}")
        else:
            await error_def()
            return

        if user_class[1]:
            for group in user_class[1]:
                class_schedule = db.fetch(
                    """SELECT schedule FROM schedules WHERE class = %s""",
                    group
                )[0][0]
                if not class_schedule:
                    await msg.answer(f"Расписание пока недоступно!")
                    return
                await msg.answer(
                    f"Расписание занятий для группы <b>{(await get_group_name_by_class_code(group)).upper()}</b>:\n\n{await schedule_converter(class_schedule)}")

    except Exception as e:
        # await error_def()
        print(e, f"\n{user_class[0]}")


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
                     "В начале сообщения желательно указать #JackBot")


@user_router.message(F.text.lower() == "настройки ⚙")
async def get_settings_cmd(msg: Message):
    if msg.chat.id in ADMINS:
        if db.fetch("""SELECT mailing FROM bot_settings""")[0][0]:
            await msg.answer(f"Доступные настройки:",
                             reply_markup=settings_keyboard.settings(
                                 url=f"https://jack.skr1pmen.ru/login?id={msg.chat.id}"))
        else:
            await msg.answer(f"Доступные настройки:",
                             reply_markup=settings_keyboard.settings(
                                 mailing=False, url=f"https://jack.skr1pmen.ru/login?id={msg.chat.id}"))
    else:
        await msg.answer(f"Доступные настройки:",
                         reply_markup=settings_keyboard.user_settings())


@user_router.message(F.text.lower() == "назад ◀")
async def back_cmd(msg: Message):
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    await msg.answer("Возвращаю в меню", reply_markup=main_keyboard.main(URL + str(user_class)))


@user_router.message(F.text.lower() == "изменить основную группу 📔")
async def edit_group_cmd(msg: Message, state: FSMContext):
    db.execute("""UPDATE users SET class = 0 WHERE chat_id = %s""", msg.chat.id)
    await state.set_state(Group.group)
    await msg.answer("Введи, пожалуйста, название группы, чтобы её изменить.\n<i>Пример: МК-22</i>")


@user_router.message(F.text.lower() == "отключить рассылку 📮")
@user_router.message(F.text.lower() == "включить рассылку 📮")
async def switching_mailing_cmd(msg: Message):
    db.execute("""UPDATE bot_settings SET mailing = not mailing""")
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    await msg.answer("Успешно❕\nНастройки были изменены.", reply_markup=main_keyboard.main(URL + str(user_class)))
    db.execute(f"""insert into logs (type, message) values ('info', 'Schedule notifications disabled/enabled')""")


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
        db.execute(f"""insert into logs (type, message) values ('error', 'User {msg.chat.id} attempted to do a mailing')""")


@user_router.message(message_text.message)
async def set_message_cmd(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data(message=msg.text)
    data = await state.get_data()
    await state.clear()
    await msg.answer("Успешно❕\nСообщение начинает рассылаться.")
    data = data["message"]
    all_users = db.fetch("""SELECT chat_id, name, class FROM users""")
    for user in all_users:  # user[0] -> id, user[1] -> user name
        try:
            if user[0] == msg.chat.id:
                continue
            await bot.send_message(
                user[0],
                data.replace("{name}", user[1])
                .replace("{my}", "@skr1pmen")
                .replace("{bot}", hlink("Jack","https://t.me/srmk_bot?start=1")),
                reply_markup=main_keyboard.main(URL + str(user[2]))
            )
        except Exception as e:
            db.execute("""DELETE FROM users WHERE chat_id = %s""", user[0])
            db.execute(f"""insert into logs (type, message) values ('error', '{e}')""")
    db.execute(f"""insert into logs (type, message) values ('info', 'User {msg.chat.id} made a distribution')""")


@user_router.message(Command('update_users_data'))
async def update_users_data(msg: Message, bot: Bot):
    if msg.chat.id in ADMINS:
        users = db.fetch("""SELECT * FROM users ORDER BY id""")
        await msg.answer('Начало обновления')
        db.execute(f"""insert into logs (type, message) values ('warning', 'Start global update user data')""")
        for user in users:
            data = await bot.get_chat(user[1])
            db.execute("""UPDATE users SET name = %s, surname = %s, username = %s WHERE chat_id = %s""", data.first_name, data.last_name, data.username, user[1])
            print(data.id)
        await msg.answer("Конец обновления!")
    else:
        await msg.answer("Ошибка❗\nТебе недоступна данная команда!")
        db.execute(
            f"""insert into logs (type, message) values ('warning', 'User {msg.chat.id} attempted to update the data of all users')""")


# Предложка
@user_router.message(F.text.lower()[:-2] == "предложить идею")
async def suggestion_ideas(msg: Message, state: FSMContext):
    await state.set_state(Suggestion.suggestion)
    await msg.answer(
        "Напиши свою идею. Если передумал, нажми 'Отменить ввод' или команду '/cancel'.",
        reply_markup=main_keyboard.suggestion_idea_kb()
    )

@user_router.message(Suggestion.suggestion)
async def set_message_cmd(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data(message=msg.text)
    text = await state.get_data()
    await state.clear()
    user_class = db.fetch("""SELECT class FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
    if text['message'].lower() in 'отменить ввод' or text['message'].lower() in '/cancel':
        await msg.answer(
            "Хорошо, но если будет предложение обязательно возвращайся.",
            reply_markup=main_keyboard.main(URL + str(user_class))
        )
    else:
        user_id = db.fetch("""SELECT id FROM users WHERE chat_id = %s""", msg.chat.id)[0][0]
        idea_id = db.fetch(
            """insert into ideas (user_id, idea) values (%s, %s) returning id""",
            user_id, text['message']
        )
        db.execute(
            f"""insert into logs (type, message) values ('info', %s)""",
            f'User {msg.chat.id} suggested idea #{idea_id[0][0]}'
        )
        await msg.answer(
            "Спасибо за твою идею! Мы её рассмотрим.",
            reply_markup=main_keyboard.main(URL + str(user_class))
        )


# Подключение к серверу
async def connect_to_server(bot: Bot):
    async with websockets.connect(config.WS_SERVER) as websocket:
        db.execute(f"""insert into logs (type, message) values ('info', 'Server connected')""")
        while True:
            message_json = await websocket.recv()
            message = json.loads(message_json)

            if message['user_id']:
                users = db.fetch("""SELECT name, class FROM users WHERE chat_id = %s""", message['user_id'])
                await bot.send_message(
                    chat_id=message["user_id"],
                    text=message["message"].replace("{name}", users[0])
                            .replace("{my}", "@skr1pmen")
                            .replace("{bot}", hlink("Jack","https://t.me/srmk_bot?start=1")),
                    reply_markup=main_keyboard.main(URL + str(user[1]))
                )
            else:
                all_users = db.fetch("""SELECT chat_id, name, class FROM users""")
                for user in all_users:  # user[0] -> id, user[1] -> user name
                    try:
                        await bot.send_message(
                            user[0],
                            message["message"].replace("{name}", user[1])
                                .replace("{my}", "@skr1pmen")
                                .replace("{bot}", hlink("Jack","https://t.me/srmk_bot?start=1")),
                            reply_markup=main_keyboard.main(URL + str(user[2]))
                        )
                    except Exception as e:
                        db.execute("""DELETE FROM users WHERE chat_id = %s""", user[0])
                        db.execute("""UPDATE statistics SET delete = delete + 1""")
                        db.execute(f"""insert into logs (type, message) values ('error', '{e}')""")
                db.execute(f"""insert into logs (type, message) values ('info', 'The mailing from the site has started')""")


# Добавление/Удаление дополнительных групп для пользователя
@user_router.message(F.text.lower()[:-2] == "дополнительные группы")
async def additional_classes_settings(msg: Message):
    groups_data = db.fetch("""select additional_classes from users where chat_id = %s""", msg.chat.id)[0][0]

    groups = 'Не указано'
    if groups_data:
        group_names = [(await get_group_name_by_class_code(group)).upper() for group in groups_data]
        groups = ', '.join(group_names) if group_names else 'Не указано'

    await msg.answer(f"Твои дополнительные группы:\n{groups}", reply_markup=additional_classes_kb.main())

@user_router.callback_query(F.data == "add_group")
async def add_group_btn(call: CallbackQuery, state: FSMContext):
    await call.answer('')

    await state.set_state(AddGroup.additional_group)

    await call.message.edit_text(
        f"Хорошо, напиши мне, пожалуйста, название группы, которую ты дополнительно хочешь отслеживать.\n<i>Например: мк-22</i>",
        reply_markup=None
    )

@user_router.message(AddGroup.additional_group)
async def additional_group(msg: Message, state: FSMContext):
    groups = db.fetch("""select class, additional_classes from users where chat_id = %s""", msg.chat.id)[0]

    await state.update_data(additional_group=msg.text)
    data = await state.get_data()
    await state.clear()

    main_group = groups[0]
    additional_group = [] if not groups[1] else groups[1]

    if data['additional_group'].lower() in group_list:
        code = group_list[data['additional_group'].lower()]
        if code == main_group or code in additional_group:
            await msg.answer("Эта группа уже отслеживается. Попробуй ещё раз ввести название группы.")
            await state.set_state(AddGroup.additional_group)
        else:
            additional_group.append(code)
            db.execute(
                """update users set additional_classes = %s where chat_id = %s""",
                additional_group, msg.chat.id
            )
            await msg.answer(
                "Хорошо, теперь ты будешь дополнительно получать расписание этой группы.",
                reply_markup=main_keyboard.main(f"{URL}{main_group}"))
    else:
        await msg.answer("Прости, но я не знаю такую группу. Попробуй ввести ещё раз!")
        await state.set_state(AddGroup.additional_group)

@user_router.callback_query(F.data == "del_group")
async def del_group_btn(call: CallbackQuery):
    groups = db.fetch("""select additional_classes from users where chat_id = %s""", call.message.chat.id)[0][0]

    await call.answer('')
    if not groups:
        await call.message.edit_text("У вас нет групп для отслеживания.")
        return
    groups_dict = {}
    for group in groups:
        groups_dict[await get_group_name_by_class_code(group)] = group
    await call.message.edit_text(
        "Выбери группу, которую нужно перестать отслеживать.",
            reply_markup=additional_classes_kb.del_group(groups_dict)
    )

@user_router.callback_query()
async def add_group_btn(call: CallbackQuery):
    groups = db.fetch("""select additional_classes from users where chat_id = %s""", call.message.chat.id)[0][0]

    await call.answer('')
    if 'delete_' in call.data:
        code = call.data[7:]
        groups.remove(int(code))
        db.execute(
            """update users set additional_classes = %s where chat_id = %s""",
            groups, call.message.chat.id
        )
        if len(groups) >= 1:
            groups_dict = {}
            for group in groups:
                groups_dict[await get_group_name_by_class_code(group)] = group
            await call.message.edit_text(
                "Выбери группу, которую нужно перестать отслеживать.",
                reply_markup=additional_classes_kb.del_group(groups_dict)
            )
        else:
            await call.message.edit_text("У вас больше нет групп для отслеживания.")


@user_router.message()
async def user_cmd(msg: Message):
    await msg.answer("Прости, но я тебя не понимаю 😞")
