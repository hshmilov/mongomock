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
