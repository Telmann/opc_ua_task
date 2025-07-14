"""
Этот модуль отвечает за эндпоинты FastAPI-приложения.
"""

import asyncio
import subprocess
import time
import uuid

# from opcua import Client, Server, ua
from asyncua import Client
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException

from app.db.update_task import poll_opcua_and_store  # с тредами
from app.models.pydantic_models import (AddTagRequest, DeleteTableRequest,
                                        DeleteTagRequest, RenameTableRequest,
                                        RenameTagRequest)
from server_sim import delete_tag_from_server

from .db.crud import (add_tag, change_table_name, check_tag,
                      create_device_table, delete_table, delete_tag,
                      rename_tag)

app = FastAPI()
STORAGE_FILE = "storage.txt"
RENAME_STORAGE_FILE = "rename_storage.txt"
running_asyncio_tasks = {}


@app.on_event("startup")
def start_c_server():
    subprocess.Popen(
        ["PATH\\\opc_ua_task\\step1\\c_server.exe"]  # путь к c_server
    )  # запуск C server


@app.post("/tables/create")
async def device_table(
    url: str,
    table_name: str,
    number_tags: int = None,  # number_tags для определения кол-ва принимаемых тэгов
) -> dict[str, str]:  # 1) принимать url сервера opcua на питоне
    """Функция, создающая таблицу с тэгами в БД (имя записывается в формате 'device_xyz', где xyz это имя введенное
    пользователем). Поле number_tags позволяет задать кол-во принимаемых тэгов c OPC UA сервера на python!
    Если не заполнить параметр number_tags, то будут приниматься и передаваться все тэги с OPC UA сервера на python.
    """
    try:
        start_time = time.time()

        client = Client(url)  # 2) передавать принятый url для подключения
        await client.connect()

        root = client.get_root_node()

        myobj = await root.get_child(["0:Objects", "2:MyObject"])

        tags = await myobj.get_children()
        if number_tags:
            tags = tags[:number_tags]

        connect_time = time.time()
        print(
            f"\n Time to connect and get tags: {connect_time - start_time:.2f} seconds\n"
        )

        # device_name = f"device_{str(uuid.uuid4())[:6]}"
        device_name = f"device_{table_name}"

        table_start = time.time()
        await create_device_table(device_name, tags)
        table_end = time.time()
        print(
            f"\n Time to create table and insert tags: {table_end - table_start:.2f} seconds\n"
        )

        # background_tasks.add_task(poll_opcua_and_store, device_name)
        task = asyncio.create_task(
            poll_opcua_and_store(device_name, url, number_tags)
        )  # 3) так же сюда передавать url для подключения у таска
        running_asyncio_tasks[device_name] = task
        # запускается асинхронный полинг, который обновляет значения тэгов.
        return {"status": "success", "device_name": device_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tables/rename")  # !
async def rename_table(
    req: RenameTableRequest, url: str, number_tags: int = None
) -> dict[str, str]:
    """Функция, которая переименовывает таблицу с тэгами в БД (в поле new_name начните имя таблицы с 'device_').
    Параметр number_tags не нужно задавать, если таблица изначально была создана без указания данного параметра
    (хотя если указать, то обновляться продолжит только указанное кол-во тэгов)"""
    try:
        await change_table_name(req.old_name, req.new_name)  # меняем имя таблицы в БД
        if req.old_name in running_asyncio_tasks:  # убиваем старый бэкграунд таск
            running_asyncio_tasks[req.old_name].cancel()
        task = asyncio.create_task(
            poll_opcua_and_store(req.new_name, url, number_tags)
        )  # создаем новый бэкграунд таск
        running_asyncio_tasks[req.new_name] = task
        return {"status": "success", "message": "Table renamed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tables/delete")
async def remove_table(req: DeleteTableRequest) -> dict[str, str]:
    """Функция, удаляющая таблицу с тэгами в БД"""
    try:
        await delete_table(req.table_name)
        return {"status": "success", "message": "Table deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/tags/rename")
async def rename_column(req: RenameTagRequest) -> dict[str, str]:
    """Функция, которая переименовывает тэг в таблице в БД"""
    try:
        check_flag = await check_tag(
            req.table_name, req.old_name
        )  # crud-функция check_tag позволяет проверить есть ли тег с таким именем в БД
        if not check_flag:  # False возвращается если тегов с таким именем нет в БД
            return {"status": "NOT success!", "message": "There is no such tag in DB!"}

        full_old_name = req.tag_type + "_" + req.old_name
        full_new_name = req.tag_type + "_" + req.new_name
        with open(RENAME_STORAGE_FILE, "a") as f:
            f.write(f"{full_old_name} {full_new_name}\n")

        time.sleep(4.0)
        await rename_tag(
            req.table_name, req.old_name, req.new_name
        )  # crud для переименования в БД
        return {"status": "success", "message": "Tag renamed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tags/delete")
async def remove_column(req: DeleteTagRequest) -> dict[str, str]:
    """Функция, которая удаляет тэг в таблице в БД"""
    try:  # Boolean_tag0
        check_flag = await check_tag(req.table_name, req.tag_name)
        if not check_flag:
            return {"status": "NOT success!", "message": "There is no such tag in DB!"}

        full_name = req.tag_type + "_" + req.tag_name

        with open(STORAGE_FILE, "a") as f:
            f.write(f"{full_name}\n")
        time.sleep(3.0)

        await delete_tag(req.table_name, req.tag_name)

        return {"status": "success", "message": "Tag deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tags/add")
async def add_column_endpoint(req: AddTagRequest) -> dict[str, str]:
    """Функция, которая добавляет тэг в таблице в БД"""
    try:
        await add_tag(req.table_name, req.tag_name, req.tag_type, req.tag_value)
        return {
            "status": "success",
            "message": f'Tag "{req.tag_name}" added to table "{req.table_name}"',
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
