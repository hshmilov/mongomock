from collections import namedtuple
DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 1000000
MAX_EXCEPTION_COUNT = 5

ServerTypes = namedtuple('kinds', ('virtual_server',
                                   'pool',
                                   'pool_members'))

SERVER_TYPES = ServerTypes(virtual_server='tm:ltm:virtual:virtualstate',
                           pool='tm:ltm:pool:poolstate',
                           pool_members='tm:ltm:pool:members:membersstate',)
