PASSWORD = 'password'
USER = 'username'
BITLOCKER_HOST = 'server'
BITLOCKER_PORT = 'port'
BITLOCKER_DATABASE = 'database'
DRIVER = 'driver'
DEFAULT_BITLOCKER_PORT = 1433
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
BITLOCKER_QUERY = 'Select * from ComplianceCore.Machines'
COMPLIANCE_QUERY = 'Select * from ComplianceCore.MachinesComplianceView'
VOLUMES_QUERY = 'Select * from ComplianceCore.Volumes'
MACHINES_VOLUMES = 'Select * from ComplianceCore.Machines_Volumes'
ENCRYPTION_STATE_DICT = {'0': 'Encrypted',
                         '1': 'Decrypted',
                         '2': 'Encrypting',
                         '3': 'Decrypting',
                         '4': 'EncryptionPaused',
                         '5': 'DecryptionPaused',
                         '6': 'Unknown'}
PROTECTION_STATE_DICT = {'0': 'ProtectionOn',
                         '1': 'ProtectionOff',
                         '2': 'Unknown'}
