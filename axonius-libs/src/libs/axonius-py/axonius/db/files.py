"""
A handler for DB uploaded files
"""
from typing import Union

import gridfs
from bson import ObjectId
from pymongo import MongoClient

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME


class DBFileHelper:
    def __init__(self, db: MongoClient):
        self.__fs = gridfs.GridFS(db[CORE_UNIQUE_NAME])

    def upload_file(self, file_contents, filename: str = None, **kwargs) -> str:
        written_file = self.__fs.put(file_contents, filename=filename, **kwargs)
        return str(written_file)

    def get_file(self, uuid: Union[str, ObjectId]) -> gridfs.GridOut:
        if isinstance(uuid, str):
            uuid = ObjectId(uuid)
        elif not isinstance(uuid, ObjectId):
            raise ValueError(f'Unknown format for uuid')

        return self.__fs.get(uuid)

    def delete_file(self, uuid: Union[str, ObjectId]):
        if isinstance(uuid, str):
            uuid = ObjectId(uuid)
        elif not isinstance(uuid, ObjectId):
            raise ValueError(f'Unknown format for uuid')
        self.__fs.delete(uuid)
