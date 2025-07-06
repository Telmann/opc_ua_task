import asyncio
import time
from datetime import datetime

from opcua import Client
from sqlalchemy import Column, MetaData, Table, insert

from app.db.db import engine, sync_engine


async def poll_opcua_and_store(device_name: str, url: str):  # принимать url
    opc_connect_start = time.time()
    client = Client(
        url
    )  # передавать url, например "opc.tcp://localhost:4840/freeopcua/server/"
    client.connect()
    opc_connect_time = time.time() - opc_connect_start
    print(f"\n connect to server (poll) time: {opc_connect_time} \n")

    root = client.get_root_node()
    myobj = root.get_child(["0:Objects", "2:MyObject"])
    metadata = MetaData()
    tag_table = Table(device_name, metadata, autoload_with=sync_engine)

    try:
        while True:
            data = []
            db_insert_start = time.time()
            tags = myobj.get_children()
            for tag in tags:
                value = str(tag.get_value())
                bname = tag.get_browse_name().Name
                tag_type, name = bname.split("_", 1)
                data.append(
                    {
                        "tag_name": name,
                        "tag_type": tag_type,
                        "tag_value": value,
                        "timestamp": datetime.utcnow(),
                    }
                )
            print(
                f" \n time for data processing: {time.time() - db_insert_start} \n"
            )  # время на обработку данных
            async with engine.begin() as conn:
                await conn.execute(tag_table.insert(), data)
            print(
                f"\n time for new data insert to db: {time.time() - db_insert_start} \n"
            )  # время на обработку и вставку в БД
            await asyncio.sleep(0.01)
    finally:
        client.disconnect()
