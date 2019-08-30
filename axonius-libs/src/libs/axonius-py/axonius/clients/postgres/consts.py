from enum import Enum


class PostgresDBSchemaNames(Enum):
    db_host = 'db_host'
    db_port = 'db_port'
    db_username = 'db_username'
    db_password = 'db_password'
    db_name = 'db_name'


COMMON_POSTGRES_MENDATORY_SCHEMA_VALUES = [
    PostgresDBSchemaNames.db_host.value,
    PostgresDBSchemaNames.db_username.value,
    PostgresDBSchemaNames.db_password.value,
    PostgresDBSchemaNames.db_name.value
]


DEFAULT_POSTGRES_PORT = 5432


COMMON_POSTGRES_DB_SCHEMA = [
    {
        'name': PostgresDBSchemaNames.db_host.value,
        'title': 'DB Host',
        'type': 'string'
    },
    {
        'name': PostgresDBSchemaNames.db_port.value,
        'title': 'DB Port',
        'type': 'integer',
        'default': DEFAULT_POSTGRES_PORT,
    },
    {
        'name': PostgresDBSchemaNames.db_username.value,
        'title': 'DB Username',
        'type': 'string'
    },
    {
        'name': PostgresDBSchemaNames.db_password.value,
        'title': 'DB Password',
        'type': 'string',
        'format': 'password'
    },
    {
        'name': PostgresDBSchemaNames.db_name.value,
        'title': 'DB Name',
        'type': 'string'
    },
]
