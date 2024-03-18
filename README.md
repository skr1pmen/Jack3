# Jack

Телеграмм бот для рассылки расписания занятий студентам колледжа СРМК.

***❕ Не шаришь не лезь, оно тебя сожрёт ❕***

---

### Принцип работы:

Раз в 15 минут бот заходит на сайт с расписанием, собирает данные, преобразует их в удобный формат.
Сравнивается с предыдущим, если новое расписание отличается от предыдущего, происходит рассылка нового расписания всем участникам бота.
Все изменения расписания сохраняются в базу данных.

---

### Технические характеристики:
* Python 3.11 и выше
* Pip 24.0 и выше
* Дополнительные пакеты:
  * aiogram 3.4.1
  * APScheduler 3.10.4
  * beautifulsoup4 4.12.3
  * aiohttp 3.9.3
  * psycopg2-binary 2.9.9

---

### Установка:

* Все необходимые пакеты можно установить через `requirements.txt`.

    pip install -r requirements.txt

* Для успешного подключения бота к API телеграмма и сайту колледжа необходимо отредактировать файл `app/config.py` следующим образом:

      TOKEN = "Здесь будет ваш токен"
      USERAGENT = {Подставьте необходимый USERAGENT}
      DATABASE = {
          "HOST": "{Хост БД}",
          "USERNAME": "Имя пользователя БД",
          "PASSWORD": "Паролль от БД",
          "BASENAME": "Название БД"
      }
      ADMINS = [id_admins(array)]  
      

* Создание базы данных. Всего в базе 5 таблиц `users`, `schedules`, `statistics`, `bot_settings` и `logs`(пока не используется).
Код для создания таблиц:
  * **users:**

        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT not null,
            name VARCHAR not null,
            surname VARCHAR,
            username VARCHAR,
            class INTEGER DEFAULT 0,
            prem BOOLEAN DEFAULT false
        );
  * **schedules:**
  
          CREATE TABLE schedules (
              class INTEGER,
              schedule JSONB
          );
  * **statistics:**
  
           CREATE TABLE statistics (
              added INTEGER,
              delete INTEGER,
           );
  * **bot_settings:**
        
        CREATE TABLE bot_settings (
            mailing BOOLEAN DEFAULT true
        );
  * **logs:**
  
        CREATE TABLE logs (
          id SERIAL PRIMARY KEY,
          time TIMESTAMP DEFAULT NOW(),
          type VARCHAR,
          message VARCHAR
        );
