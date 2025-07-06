# opc_ua_task

# Python-код реализован с помощью Python 3.11, SQLAlchemy, FastAPI
## Описание проекта: возможен запуск opc ua сервера/серверов на python (генерирующих нужное кол-во тегов), FastAPI приложение позволяет создавать таблицу в БД с тегами(обновляются в режиме реального времени), вместе с FastAPI приложением автоматически запускается opc ua сервер на C, который для каждой таблицы в БД создает объект на сервере и записывает в объект теги из БД, обновляя их.

## Описание скорости работы: ...


# Перед запуском FastAPI приложения необходимо запустить сервер на python.

## Чтобы забилдить C сервер:
1) Для создания .exe сервера выполнить:
```bash
gcc -std=c99 open62541.c c_server.c -I"PATH_TO_\PostgreSQL\version\include" -L"PATH_TO\PostgreSQL\version\lib" -lpq -lws2_32 -liphlpapi -o name_c_server.exe
```
2) Необходимо указать путь до C сервера(в строке №31 в файле main.py), так как он запускается вместе с FastAPI приложением:

## Для запуска py сервера (порт 4841 занят С сервером):
```bash
python server_sim.py number_tags opc.tcp://localhost:PORT/freeopcua/server/
```
# После запуска py сервера, можно запустить FastAPI-приложение, введя в терминале в корне проекта:
```
uvicorn app.main:app --reload
```
## Теперь можно обращаться к эндпоинтам по локальному адресу: "http://127.0.0.1:8000/docs#/"

### Пример эндпоинтов:
Необходимо отметить, что выполнение операции добавления тэга на данный момент просто добавляет тэг (только его имя, тип и значение) в БД и на C сервер(без timestamp и обновлений значения).
![image](https://github.com/user-attachments/assets/891f517c-42ed-4776-8075-dfff6ba000a1)
![image](https://github.com/user-attachments/assets/40b91ee8-e34b-4ca8-b4ea-5e0e5f02d121)


### Пример таблицы в БД:
![image](https://github.com/user-attachments/assets/c461111b-d49d-49d3-a46d-d9140f80b4a1)


Пример объектов на С сервере:

![image](https://github.com/user-attachments/assets/0abb5eb2-6f8c-49d8-99d9-148749b56910)

![image](https://github.com/user-attachments/assets/0d94ec80-deda-4e2c-bd23-9dc637364e2a)

