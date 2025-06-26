"""
Этот модуль отвечает за эндпоинты FastAPI-приложения.
"""

import uuid

from fastapi import FastAPI, HTTPException
from opcua import Client

from app.models.pydantic_models import (AddTagRequest, DeleteTableRequest,
                                        DeleteTagRequest, RenameTableRequest,
                                        RenameTagRequest)

from .db.crud import (add_tag, change_table_name, create_device_table,
                      delete_table, delete_tag, rename_tag)

app = FastAPI()


@app.post("/tables/create")
async def device_table() -> dict[str, str]:
    """Функция, создающая таблицу с тэгами в БД"""
    try:
        client = Client("opc.tcp://localhost:4840/freeopcua/server/")
        client.connect()

        root = client.get_root_node()

        myobj = root.get_child(["0:Objects", "2:MyObject"])

        tags = myobj.get_children()
        print(tags[:25])

        device_name = f"device_{str(uuid.uuid4())[:6]}"
        await create_device_table(device_name, tags)

        return {"status": "success", "device_name": device_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tables/rename")
async def rename_table(req: RenameTableRequest) -> dict[str, str]:
    """Функция, которая переименовывает таблицу с тэгами в БД"""
    try:
        await change_table_name(req.old_name, req.new_name)
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
        await rename_tag(req.table_name, req.old_name, req.new_name)
        return {"status": "success", "message": "Tag renamed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tags/delete")
async def remove_column(req: DeleteTagRequest) -> dict[str, str]:
    """Функция, которая удаляет тэг в таблице в БД"""
    try:
        await delete_tag(req.table_name, req.tag_name)
        return {"status": "success", "message": "Tag deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tags/add")
async def add_column_endpoint(req: AddTagRequest) -> dict[str, str]:
    """Функция, которая добавляет тэг в таблице в БД"""
    try:
        await add_tag(req.table_name, req.tag_name, req.tag_type)
        return {
            "status": "success",
            "message": f'Tag "{req.tag_name}" added to table "{req.table_name}"',
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
