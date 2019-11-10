from enum import Enum, auto


class SSLState(Enum):
    Unencrypted = auto()
    Verified = auto()
    Unverified = auto()


MANDATORY_SSL_CONFIG_SCHEMA = [
    {
        'name': 'cert_file',
        'title': 'Certificate File',
        'description': 'The binary contents of the cert_file',
        'type': 'file',
    },
    {
        'name': 'private_key',
        'title': 'Private Key File',
        'description': 'The binary contents of the private_key',
        'type': 'file',
    }
]

MANDATORY_SSL_CONFIG_SCHEMA_DEFAULTS = {
    'cert_file': None,
    'private_key': None
}

COMMON_SSL_CONFIG_SCHEMA_CA_ONLY = [
    {
        'name': 'use_ssl',
        'title': 'Use SSL for Connection',
        'type': 'string',
        'enum': [SSLState.Unencrypted.name, SSLState.Verified.name, SSLState.Unverified.name],
        'default': SSLState.Unencrypted.name,
    },
    {
        'name': 'ca_file',
        'title': 'CA File',
        'description': 'The binary contents of the ca_file',
        'type': 'file',
    }
]

COMMON_SSL_CONFIG_SCHEMA = [
    *COMMON_SSL_CONFIG_SCHEMA_CA_ONLY,
    *MANDATORY_SSL_CONFIG_SCHEMA
]

COMMON_SSL_CONFIG_SCHEMA_DEFAULTS = {
    'use_ssl': SSLState.Unencrypted.name,
    'ca_file': None,
    **MANDATORY_SSL_CONFIG_SCHEMA_DEFAULTS
}
