from enum import Enum

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter


class SQLServers(Enum):
    MSSQL = 'MSSQL'
    Postgres = 'PostgreSQL'
    MySQL = 'MySQL'
    Oracle = 'Oracle'


class SQLDatabases(Enum):
    SQLite = 'SQLite'


class SQLTypes(Enum):
    MSSQL = SQLServers.MSSQL.value
    POSTGRES = SQLServers.Postgres.value
    MYSQL = SQLServers.MySQL.value
    SQLITE = SQLDatabases.SQLite.value


class MySqlAdapter(DeviceAdapter):
    server_tag = Field(str, 'Server Tag')
    database = Field(str, 'DB Name')
    table = Field(str, 'Table Name')
