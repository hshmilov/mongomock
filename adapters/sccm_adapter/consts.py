PASSWORD = 'password'
USER = 'username'
SCCM_HOST = 'server'
SCCM_PORT = 'port'
SCCM_DATABASE = 'database'
DRIVER = 'driver'
DEFAULT_SCCM_PORT = 1433
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
SCCM_QUERY = """
SELECT *,
        [Network Interfaces] = STUFF((SELECT ';' + rasi.MACAddress0 + '@' + rasi.IPAddress0
                FROM v_GS_NETWORK_ADAPTER_CONFIGURATION AS rasi
                WHERE rasi.ResourceID = SYS.ResourceID
                FOR XML PATH, TYPE).value(N'.[1]',N'nvarchar(max)'),1,1,''),
        [Mac Addresses] = STUFF((SELECT ';' + rasi.MACAddress0
                FROM v_GS_NETWORK_ADAPTER_CONFIGURATION AS rasi
                WHERE rasi.ResourceID = SYS.ResourceID
                FOR XML PATH, TYPE).value(N'.[1]',N'nvarchar(max)'),1,1,''),
        [IP Addresses] = STUFF((SELECT ';' + rasi.IPAddress0
                FROM v_GS_NETWORK_ADAPTER_CONFIGURATION AS rasi
                WHERE rasi.ResourceID = SYS.ResourceID
                FOR XML PATH, TYPE).value(N'.[1]',N'nvarchar(max)'),1,1,''),
        [Last Seen] = v_CH_ClientSummary.LastActiveTime
FROM v_R_SYSTEM SYS
LEFT JOIN v_GS_COMPUTER_SYSTEM on SYS.ResourceID = v_GS_COMPUTER_SYSTEM.ResourceID
LEFT JOIN v_CH_ClientSummary on v_CH_ClientSummary.ResourceID = SYS.ResourceID 
LEFT JOIN v_GS_OPERATING_SYSTEM on SYS.ResourceID = v_GS_OPERATING_SYSTEM.ResourceID
{0}
"""
LIMIT_SCCM_QUERY = """
WHERE DATEDIFF(dd,v_CH_ClientSummary.LastActiveTime,GETDATE())<{0}/24.0;
"""
QUERY_SOFTWARE = 'Select ResourceID, ProductName0, ProductVersion0 from v_GS_INSTALLED_SOFTWARE'
QUERY_PATCH = 'Select ResourceID, Description0, FixComments0, InstallDate0, HotFixID0 from v_GS_QUICK_FIX_ENGINEERING'
QUERY_PROGRAM = 'Select ResourceID, DisplayName0, Version0 from v_GS_ADD_REMOVE_PROGRAMS'
QUERY_PROGRAM_2 = 'Select ResourceID, DisplayName0, Version0 from v_GS_ADD_REMOVE_PROGRAMS_64'
BIOS_QUERY = 'Select ResourceID, SerialNumber0, Manufacturer0 from v_GS_PC_BIOS'
USERS_QUERY = 'Select MachineResourceID, UniqueUserName from v_UserMachineRelation'
USERS_TOP_QUERY = 'Select ResourceID, TopConsoleUser0 from v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP'
MALWARE_QUERY = 'Select ResourceID, EngineVersion, Version, LastFullScanDateTimeEnd, ' \
                'ProductStatus, LastQuickScanDateTimeEnd, Enabled from v_GS_AntimalwareHealthStatus'
LENOVO_QUERY = 'select ResourceID, Version0 from v_GS_COMPUTER_SYSTEM_PRODUCT'
CHASIS_QUERY = 'select ResourceID, ChassisTypes0 from v_GS_SYSTEM_ENCLOSURE'
