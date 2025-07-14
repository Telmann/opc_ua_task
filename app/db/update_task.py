import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from asyncua import Client
from sqlalchemy import MetaData, Table

from app.db.db import engine, sync_engine

# executor = ThreadPoolExecutor(max_workers=500)  # Можно настроить под нагрузку

count = 0.0


async def process_tag(tag):
    try:
        # start_query = time.time()
        get_val = await tag.read_value()
        value = str(get_val)

        bname = await tag.read_browse_name()
        tag_type, name = bname.Name.split("_", 1)

        # print(f"\n Single TIME FOR GETTING STUFF FROM OPC UA PYTHON SERVER {time.time() - start_query} \n")

        return {
            "tag_name": name,
            "tag_type": tag_type,
            "tag_value": value,
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        print(e)


async def collect_data(tags, batch_size=500):  # batch
    # loop = asyncio.get_event_loop()
    res_arr = []

    for i in range(0, len(tags), batch_size):
        batch = tags[i : i + batch_size]

        # tasks = [loop.run_in_executor(executor, partial(process_tag, tag)) for tag in batch]
        tasks = [process_tag(tag) for tag in batch]
        batch_res = await asyncio.gather(*tasks)
        res_arr.extend(r for r in batch_res if r is not None)

    return res_arr


async def poll_opcua_and_store(device_name: str, url: str, number_tags: int = None):
    opc_connect_start = time.time()
    client = Client(url)
    await client.connect()

    print(
        f"\n connect to server (poll) time: {time.time() - opc_connect_start:.2f} sec \n"
    )

    root = client.get_root_node()
    myobj = await root.get_child(["0:Objects", "2:MyObject"])

    metadata = MetaData()
    tag_table = Table(device_name, metadata, autoload_with=sync_engine)

    try:
        while True:
            db_insert_start = time.time()
            tags = await myobj.get_children()
            if number_tags:
                tags = tags[:number_tags]

            data = await collect_data(tags)

            print(
                f"\n time for data processing: {time.time() - db_insert_start:.2f} sec \n"
            )

            async with engine.begin() as conn:
                await conn.execute(tag_table.insert(), data)

            print(
                f"\n total time including db insert: {time.time() - db_insert_start:.2f} sec \n"
            )
            await asyncio.sleep(1)
    finally:
        await client.disconnect()
