from axonius.utils.parsing import normalize_mac

# This macs aren't unique so don't parse them as fdbs and arps
JUNIPER_NON_UNIQUE_MACS = [
    '50:50:54:50:30:30',
    '00:0B:CA:FE:00:00',
    '00:0B:CA:FE:00:01',
    '20:41:53:59:4E:FF',
    '00:05:9a:3c:7a:00',
    '02:00:00:00:00:0A',
    '02:00:00:00:00:0B'
]

# https://knowledgebase.paloaltonetworks.com/KCSArticleDetail?id=kA10g000000CmAOCA0

PANW_NON_UNIQUE_MACS = [
    '02:50:41:00:00:01',
]


ALL_BLACKLIST = [normalize_mac(mac) for mac in JUNIPER_NON_UNIQUE_MACS + PANW_NON_UNIQUE_MACS]
