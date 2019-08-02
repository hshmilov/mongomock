PASSWORD = 'password'
USER = 'username'
LANSWEEPER_HOST = 'server'
LANSWEEPER_PORT = 'port'
LANSWEEPER_DATABASE = 'database'
DRIVER = 'driver'
DEFAULT_LANSWEEPER_PORT = 1433
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
LANSWEEPER_QUERY_DEVICES = 'Select * from tblAssets'
QUERY_SOFTWARE = 'Select * from tblSoftware'
QUERY_SOFTWARE_2 = 'Select * from tblSoftwareUni'
QUERY_HOTFIX = 'Select * from tblQuickFixEngineeringHist'
QUERY_HOTFIX_2 = 'Select * from tblQuickFixEngineeringUni'
QUERY_REGISTRY = 'Select * from tblRegistry'
BIOS_QUERY = 'Select * from tblBIOS'
QUERY_AUTORUNS = 'Select * from tblAutorun'
QUERY_AUTORUNS_2 = 'Select * from tblAutorunLoc'
QUERY_AUTORUNS_3 = 'Select * from tblAutorunUni'
PROCESSES_QUERY = 'Select * from tblProcesses'
USERS_GROUPS_QUERY = 'Select * from tblUsersInGroup'
LANSWEEPER_TYPE_DICT = {'-1': 'Windows',
                        '0': 'Unknown',
                        '1': 'Network device',
                        '2': 'Firewall',
                        '3': 'NAS',
                        '4': 'Router',
                        '5': 'SAN',
                        '6': 'Switch',
                        '7': 'Tape device',
                        '8': 'Telephone system',
                        '9': 'Video device',
                        '10': 'VOIP phone',
                        '11': 'Linux',
                        '12': 'Unix',
                        '13': 'Apple Mac',
                        '14': 'Fax',
                        '15': 'Webserver',
                        '16': 'Printer',
                        '17': 'Wireless Access point',
                        '18': 'ESXi server',
                        '19': 'Fibre switch',
                        '20': 'UPS',
                        '21': 'KVM switch',
                        '22': 'Windows CE',
                        '23': 'Badge reader',
                        '24': 'Camera',
                        '25': 'Terminal',
                        '26': 'VPN device',
                        '27': 'SSL/VPN device',
                        '28': 'Environment monitor',
                        '29': 'Power injector',
                        '30': 'VOIP Gateway',
                        '31': 'xDSL router',
                        '32': 'xDSL modem',
                        '33': 'Alarm system',
                        '34': 'DSLAM device',
                        '35': 'Cable modem',
                        '36': 'APC',
                        '37': 'Multiplexer',
                        '38': 'Remote Access Controller',
                        '39': 'Device server',
                        '40': 'Hub',
                        '41': 'Bridge',
                        '42': 'Load balancer',
                        '43': 'MSFC',
                        '44': 'Probe',
                        '45': 'RSFC',
                        '46': 'RSM',
                        '47': 'Terminal server',
                        '48': 'Host',
                        '49': 'Balancer',
                        '50': 'IP gateway',
                        '51': 'Identity mgmt device',
                        '52': 'Citrix XenServer',
                        '53': 'Mail server',
                        '54': 'Wireless controller',
                        '55': 'Handheld',
                        '56': 'Power distribution unit',
                        '57': 'FTP server',
                        '58': 'Intrusion detection system',
                        '59': 'Security appliance',
                        '60': 'QOS device',
                        '61': 'Proxy server',
                        '62': 'DNS server',
                        '63': 'Management device',
                        '64': 'Blade server',
                        '65': 'Music system',
                        '66': 'Location',
                        '67': 'Rack',
                        '68': 'IOS',
                        '69': 'Vmware vCenter server',
                        '70': 'Vmware Guest',
                        '71': 'Citrix Pool',
                        '72': 'Citrix Guest',
                        '200': 'Android',
                        '201': 'Cell phone',
                        '202': 'E-reader',
                        '203': 'External disk',
                        '204': 'iPad',
                        '205': 'iPod',
                        '206': 'iPhone',
                        '207': 'Memory stick',
                        '208': 'Monitor',
                        '210': 'Projector',
                        '211': 'Scanner',
                        '212': 'Tablet',
                        '900': 'Mouse'}
BAD_TYPES = ['Mouse',
             'Monitor',
             'Projector',
             ]
