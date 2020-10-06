from datetime import datetime
from enum import Enum

from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter


class SQLServers(Enum):
    MSSQL = 'MSSQL'
    Postgres = 'PostgreSQL'
    MySQL = 'MySQL'
    Oracle = 'Oracle'
    HyperSQL = 'HyperSQL'


class SQLDatabases(Enum):
    SQLite = 'SQLite'


class SQLTypes(Enum):
    MSSQL = SQLServers.MSSQL.value
    POSTGRES = SQLServers.Postgres.value
    MYSQL = SQLServers.MySQL.value
    SQLITE = SQLDatabases.SQLite.value
    HYPERSQL = SQLServers.HyperSQL.value


class MySqlAdapter(DeviceAdapter):
    server_tag = Field(str, 'Server Tag')
    database = Field(str, 'DB Name')
    table = Field(str, 'Table Name')
    config_type_id = Field(str, 'Config Type ID')
    config_type_name = Field(str, 'Config Type Name')
    creation_time = Field(datetime, 'Creation Time')
    created_by = Field(str, 'Created By')
    last_modified = Field(datetime, 'Last Modified')
    last_modified_by = Field(str, 'Last Modified By')
    owner_team = Field(str, 'Owner Team')
    asset_tag = Field(str, 'Asset Tag')
    building = Field(str, 'Building')
    location_floor = Field(str, 'Location Floor')
    asset_status = Field(str, 'Asset Status')
    primary_username = Field(str, 'Primary Assigned User')
    asset_type = Field(str, 'Asset Type')
    last_discovery_date = Field(datetime, 'Last Discovery Date')
    last_inventory_date = Field(datetime, 'Last Inventory Date')
    data_source = Field(str, 'Data Source')
    asset_id = Field(str, 'Asset ID')
    last_logged_user = Field(str, 'Last Logged User')


class MySqlUserAdapter(UserAdapter):
    server_tag = Field(str, 'Server Tag')
    database = Field(str, 'DB Name')
    table = Field(str, 'Table Name')
