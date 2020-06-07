from enum import Enum

PASSWORD = 'password'
USER = 'username'
FLEXERA_HOST = 'server'
FLEXERA_PORT = 'port'
FLEXERA_DATABASE = 'database'
FLEXERA_DATABASE_TYPE = 'database_type'
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


# FNMP TABLES
FNMP_BASE_QUERY = f'' \
    f'select  ' \
    f'cc.*, ' \
    f'cd.QualifiedName as DomainQualifiedName, ' \
    f'gel.GroupCN as LocationName, ' \
    f'gebu.GroupCN as BusinessUnit, ' \
    f'gecc.GroupCN as CostCenter, ' \
    f'cu.UserName as AssignedUserUserName, cu.Email as AssignedUserEmail,' \
    f'csp.Name as CloudServiceProviderName, ' \
    f'vm.VMName as VMName, vm.VMTypeID as VMTypeID, vm.VirtualMachineID as VMID ' \
    f'FROM ComplianceComputer cc ' \
    f'LEFT JOIN ComplianceDomain cd on cc.ComplianceDomainID = cd.ComplianceDomainID ' \
    f'LEFT JOIN GroupEx gel on cc.LocationID = gel.GroupExID ' \
    f'LEFT JOIN GroupEx gebu on cc.BusinessUnitID = gebu.GroupExID ' \
    f'LEFT JOIN GroupEx gecc on cc.CostCenterID = gecc.GroupExID ' \
    f'LEFT JOIN ComplianceUser cu on cc.AssignedUserID = cu.ComplianceUserID ' \
    f'LEFT JOIN CloudServiceProvider csp on cc.CloudServiceProviderID = csp.CloudServiceProviderID ' \
    f'LEFT JOIN VirtualMachine vm on cc.ComplianceComputerID = vm.HostComplianceComputerID '


class FlexeraDBType(Enum):
    IM = 'IM'
    FNMP = 'FNMP'
