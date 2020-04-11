PASSWORD = 'password'
USER = 'username'
FLEXERA_HOST = 'server'
FLEXERA_PORT = 'port'
FLEXERA_DATABASE = 'database'
DRIVER = 'driver'
DEFAULT_FLEXERA_PORT = 1433
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'

BASE_TABLE = 'ComputerSystem'
COMPUTER_SYSTEM_CORRELATION = [
    'NetworkAdapterConfiguration',
    'ComputerDirectory',
    'ComputerOperatingSystem',
    'LogicalDisk',
    'ComputerUsage',
    'ComputerBIOS'
]

USER_QUERY = 'select * from [User]'     # User is a keyword in SQL
COMPUTER_RESOURCE_DETAIL = 'select * from ComputerResourceDetails'
