"""
Этот модуль отвечает за pydantic схемы/модели
"""

from pydantic import BaseModel, field_validator

types = ["Double", "Int", "Boolean", "ByteString", "XmlElement"]


class RenameTableRequest(BaseModel):
    old_name: str
    new_name: str


class DeleteTableRequest(BaseModel):
    table_name: str


class AddTagRequest(BaseModel):
    table_name: str
    tag_name: str
    tag_type: str

    @field_validator("tag_type")
    @classmethod
    def validate_type(cls, ttype: str) -> str:
        if ttype not in types:
            raise ValueError(f"Invalid tag_type '{ttype}'. Must be one of {types}")
        return ttype


class RenameTagRequest(BaseModel):
    table_name: str
    old_name: str
    new_name: str


class DeleteTagRequest(BaseModel):
    table_name: str
    tag_name: str
