PASSWORD = 'password'
USER = 'username'
FORCEPOINT_HOST = 'server'
FORCEPOINT_PORT = 'port'
FORCEPOINT_DATABASE = 'database'
DRIVER = 'driver'
DEFAULT_FORCEPOINT_PORT = 1433
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
FORCEPOINT_QUERY = 'SELECT hostname.STR_VALUE AS "Hostname",ips.STR_VALUE AS "IP Address",loginUser.STR_VALUE AS ' \
                   '"Logged-in Users",(UPDATE_DATE) AS "Last Update",profile.STR_VALUE AS ' \
                   '"Profile Name",sync.STR_VALUE AS "Version",machinetype.STR_VALUE as ' \
                   '"Machine Type",synced.INT_VALUE as "Synced",clientStatus.STR_VALUE as ' \
                   '"ClientStatus",macaddress.STR_VALUE as "MacAddress", ' \
                   'clientInstallationVersion.STR_VALUE as "ClientInstallationVersion", ' \
                   'lastProfileUpdate.TIME_VALUE_TS as "LastProfileUpdate", ' \
                   'lastPolicyUpdate.TIME_VALUE_TS as "LastPolicyUpdate", ' \
                   'operationStatus.STR_VALUE  as "OperationStatus", ' \
                   'profileVersion.INT_VALUE as "ProfileVersion" ' \
                   'FROM PA_DYNAMIC_STATUS ' \
                   'AS endpoint LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS hostname on endpoint.ID =' \
                   ' hostname.DYNAMIC_STATUS_ID and hostname.NAME = \'eps_os_HostName\' LEFT OUTER JOIN ' \
                   'PA_DYNAMIC_STATUS_PROPS ips on endpoint.ID = ips.DYNAMIC_STATUS_ID and ' \
                   'ips.NAME = \'eps_os_IPAddress\' LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS loginUser ' \
                   'on endpoint.ID = loginUser.DYNAMIC_STATUS_ID and loginUser.NAME = \'eps_os_LoggedInUsers\' ' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS profile on endpoint.ID = profile.DYNAMIC_STATUS_ID ' \
                   'and profile.NAME = \'eps_os_ProfileName\' LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS sync on ' \
                   'endpoint.ID = sync.DYNAMIC_STATUS_ID and sync.NAME = \'eps_os_AgentInstallationVersion\' LEFT ' \
                   'OUTER JOIN PA_DYNAMIC_STATUS_PROPS machinetype on endpoint.ID = machinetype.DYNAMIC_STATUS_ID ' \
                   'and machinetype.NAME = \'eps_os_MachineType\' LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS synced on ' \
                   'endpoint.ID = synced.DYNAMIC_STATUS_ID and synced.NAME= \'eps_os_Synced\' LEFT OUTER ' \
                   'JOIN PA_DYNAMIC_STATUS_PROPS clientStatus on endpoint.ID = clientStatus.DYNAMIC_STATUS_ID and ' \
                   'clientStatus.NAME = \'eps_os_ClientStatus\' LEFT OUTER JOIN ' \
                   'PA_DYNAMIC_STATUS_PROPS macaddress on ' \
                   'endpoint.ID = macaddress.DYNAMIC_STATUS_ID and macaddress.NAME = \'eps_os_MacAddress\' ' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS clientInstallationVersion on ' \
                   'endpoint.ID = clientInstallationVersion.DYNAMIC_STATUS_ID ' \
                   'and clientInstallationVersion.NAME = \'eps_os_ClientInstallationVersion\'' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS lastProfileUpdate on ' \
                   'endpoint.ID = lastProfileUpdate.DYNAMIC_STATUS_ID ' \
                   'and lastProfileUpdate.NAME = \'eps_os_LastProfileUpdate\'' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS profileVersion on ' \
                   'endpoint.ID = profileVersion.DYNAMIC_STATUS_ID ' \
                   'and profileVersion.NAME = \'eps_os_ProfileVersion\'' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS operationStatus on ' \
                   'endpoint.ID = operationStatus.DYNAMIC_STATUS_ID ' \
                   'and operationStatus.NAME = \'eps_os_OperationStatus\'' \
                   'LEFT OUTER JOIN PA_DYNAMIC_STATUS_PROPS lastPolicyUpdate on ' \
                   'endpoint.ID = lastPolicyUpdate.DYNAMIC_STATUS_ID ' \
                   'and lastPolicyUpdate.NAME = \'eps_os_LastPolicyUpdate\''
