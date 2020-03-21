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

SCCM_MAIN_QUERY = 'Select * from v_R_SYSTEM'

NICS_QUERY = 'Select MACAddress0, IPAddress0, ResourceID from v_GS_NETWORK_ADAPTER_CONFIGURATION'
COMPUTER_SYSTEM_QUERY = 'Select ResourceID, Caption0, Model0, SystemType0, UserName0, CurrentTimeZone0 from v_GS_COMPUTER_SYSTEM'
CLIENT_SUMMARY_QUERY = 'Select ResourceID, LastActiveTime from v_CH_ClientSummary'
OS_DATA_QUERY = 'Select ResourceID, LastBootUpTime0 from v_GS_OPERATING_SYSTEM'


QUERY_SOFTWARE = 'Select ResourceID, ProductName0, ProductVersion0 from v_GS_INSTALLED_SOFTWARE'
QUERY_PATCH = 'Select ResourceID, Description0, FixComments0, InstallDate0, HotFixID0 from v_GS_QUICK_FIX_ENGINEERING'
QUERY_PATCH_2 = 'Select ResourceID, Description0, FixComments0, InstallDate0, HotFixID0 from v_HS_QUICK_FIX_ENGINEERING'
QUERY_PROGRAM = 'Select ResourceID, DisplayName0, Version0 from v_GS_ADD_REMOVE_PROGRAMS'
QUERY_PROGRAM_2 = 'Select ResourceID, DisplayName0, Version0 from v_GS_ADD_REMOVE_PROGRAMS_64'
BIOS_QUERY = 'Select ResourceID, SerialNumber0, Manufacturer0 from v_GS_PC_BIOS'
USERS_QUERY = 'Select MachineResourceID, UniqueUserName from v_UserMachineRelation'
USERS_TOP_QUERY = 'Select ResourceID, TopConsoleUser0 from v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP'
MALWARE_QUERY = 'Select ResourceID, EngineVersion, Version, LastFullScanDateTimeEnd, ' \
                'ProductStatus, LastQuickScanDateTimeEnd, Enabled from v_GS_AntimalwareHealthStatus'
LENOVO_QUERY = 'select ResourceID, Version0 from v_GS_COMPUTER_SYSTEM_PRODUCT'
CHASIS_QUERY = 'select ResourceID, ChassisTypes0 from v_GS_SYSTEM_ENCLOSURE'
ENCRYPTION_QUERY = 'select ResourceID,DriveLetter0,ProtectionStatus0 from v_GS_ENCRYPTABLE_VOLUME'
VM_QUERY = 'select ResourceID, ' \
           'DNSName0, IPAddress0, State0, VMName0, Path0, Type0, TimeStamp from V_GS_VIRTUAL_MACHINES'
OWNER_QUERY = 'select * from OWNERINFO_DATA'
TPM_QUERY = 'select ResourceID, IsActivated_InitialValue0, IsEnabled_InitialValue0, IsOwned_InitialValue0 from v_GS_TPM'
COLLECTIONS_QUERY = 'select ResourceID, CollectionID from v_FullCollectionMembership'
COLLECTIONS_DATA_QUERY = 'select CollectionID, Name from v_Collection'
COMPLIANCE_QUERY = 'select ResourceID, Status from v_UpdateComplianceStatus'
LOCAL_ADMIN_QUERY = 'select ResourceID, name0 , account0, domain0 from v_gs_localgroupmembers0'
DRIVERS_QUERY = 'select ResourceID, Name0, Description0, DriverVersion0 from v_GS_VIDEO_CONTROLLER'
RAM_QUERY = 'select ResourceID, Capacity0 from v_GS_PHYSICAL_MEMORY'
NETWORK_DRIVERS_QUERY = 'select ResourceID, DriverDesc0, DriverVersion0 , ProviderName0, DriverDate0 from v_GS_NETWORK_DRIVERS'
