# opc_ua_task

# Python-код реализован с помощью Python 3.11, SQLAlchemy, FastAPI

# Перед запуском FastAPI приложения необходимо запустить сервер на python ИЛИ C.
## Для запуска C сервера:
1) Для создания .exe сервера ввести (в папке с source.c файлом):
```bash
gcc -std=c99 open62541.c source.c -lws2_32 -liphlpapi -o name_server.exe
```
2) Для запуска сервера на num (не более 10000) тэгов:
```bash
./name_server.exe num
```
## Для запуска py сервера:
```bash
python server_sim.py num
```
# После запуска сервера, можно запустить FastAPI-приложение, введя в терминале в корне проекта:
```
uvicorn app.main:app --reload
```
