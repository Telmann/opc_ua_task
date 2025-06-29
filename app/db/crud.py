"""
Модуль содержит CRUD-функции для работы с БД.
"""

from sqlalchemy import Column, Integer, String, Table, delete, text, update

from app.db.db import Base, engine, metadata, sync_engine


async def create_device_table(device_name: str, tags: list) -> None:
    table_name = f"{device_name}"
    tag_table = Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("tag_name", String, nullable=False),
        Column("tag_type", String, nullable=False),
        Column("tag_value", String, nullable=False), # !!!
    )

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        # print(len(tags), tags)
        insert_data = []
        for tag in tags:
            tag_value = str(tag.get_value())
            bname = tag.get_browse_name().Name
            tag_type, name = bname.split("_", 1)
            insert_data.append({"tag_name": name, "tag_type": tag_type, "tag_value": tag_value}) # !!!
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


async def add_tag(table_name: str, tag_name: str, tag_type: str, tag_value: str) -> None:
    tag_table = Table(table_name, metadata, autoload_with=sync_engine)
    async with engine.begin() as conn:
        stmt = tag_table.insert().values(tag_name=tag_name, tag_type=tag_type, tag_value=tag_value)
        await conn.execute(stmt)
