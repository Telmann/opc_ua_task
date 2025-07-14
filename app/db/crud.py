"""
Модуль содержит CRUD-функции для работы с БД.
"""

from datetime import datetime

from sqlalchemy import (Column, DateTime, Integer, String, Table, delete,
                        select, text, update)

from app.db.db import Base, engine, metadata, sync_engine
from app.db.update_task import collect_data


async def create_device_table(device_name: str, tags: list) -> None:
    table_name = f"{device_name}"
    tag_table = Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("tag_name", String, nullable=False),
        Column("tag_type", String, nullable=False),
        Column("tag_value", String, nullable=False),  #
        Column("timestamp", DateTime, primary_key=True, default=datetime.utcnow),
    )

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        await conn.execute(
            text(
                f"""
            SELECT create_hypertable('{table_name}', 'timestamp', if_not_exists => TRUE);
        """
            )
        )
        # insert_data = []
        insert_data = await collect_data(tags)
        '''for tag in tags:
            tag_value = str(tag.get_value())
            bname = tag.get_browse_name().Name
            tag_type, name = bname.split("_", 1)
            insert_data.append(
                {
                    "tag_name": name,
                    "tag_type": tag_type,
                    "tag_value": tag_value,
                    "timestamp": datetime.utcnow(),
                }
            )  # '''
        await conn.execute(tag_table.insert(), insert_data)


async def change_table_name(old_name: str, new_name: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"ALTER TABLE {old_name} RENAME TO {new_name}"))


async def delete_table(table_name: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


async def rename_tag(table_name: str, old_name: str, new_name: str) -> None:
    metadata.reflect(bind=sync_engine)
    tag_table = Table(table_name, metadata, autoload_with=sync_engine)

    async with engine.begin() as conn:
        stmt = (
            update(tag_table)
            .where(tag_table.c.tag_name == old_name)
            .values(tag_name=new_name)
        )
        await conn.execute(stmt)


async def delete_tag(table_name: str, tag_name: str) -> None:
    tag_table = Table(table_name, metadata, autoload_with=sync_engine)

    async with engine.begin() as conn:
        stmt = delete(tag_table).where(tag_table.c.tag_name == tag_name)
        await conn.execute(stmt)


async def add_tag(
    table_name: str, tag_name: str, tag_type: str, tag_value: str
) -> None:
    tag_table = Table(table_name, metadata, autoload_with=sync_engine)
    async with engine.begin() as conn:
        stmt = tag_table.insert().values(
            tag_name=tag_name, tag_type=tag_type, tag_value=tag_value
        )
        await conn.execute(stmt)


async def check_tag(table_name: str, tag_name: str):
    tag_table = Table(table_name, metadata, autoload_with=sync_engine)
    async with engine.begin() as conn:
        stmt = select(tag_table).where(tag_table.c.tag_name == tag_name)
        res = await conn.execute(stmt)
        return res.fetchone() is not None  # True если результат не пустой
