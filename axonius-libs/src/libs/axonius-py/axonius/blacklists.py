from axonius.utils.parsing import normalize_mac

# This macs aren't unique so don't parse them as fdbs and arps
JUNIPER_NON_UNIQUE_MACS = [
    '50:50:54:50:30:30',
    '00:0B:CA:FE:00:00',
    '00:0B:CA:FE:00:01',
    '20:41:53:59:4E:FF',
    '00:05:9a:3c:7a:00',
    '02:00:00:00:00:0*',
]

# https://knowledgebase.paloaltonetworks.com/KCSArticleDetail?id=kA10g000000CmAOCA0

FROM_FIELDS_BLACK_LIST = ['02:50:41:00:01:01', '02:50:41:00:00:01', 'EE:EE:EE:EE:EE:EE', '02:50:56:3F:00:00',
                          '02:00:4C:4F:4F:50', '00:15:5D:BA:6B:B6', '00:E0:4C:68:2D:3D',
                          '56:84:7A:FE:97:99', '00:A0:C6:00:00:00', '00:AB:00:00:00:00']

FROM_FIELDS_BLACK_LIST_REG = ['00090F**0001', 'F0D5BF******', '****20524153', '0A00270000**',
                              'ACED5C******', '005056C000**', '02504100****', 'ACDE48******']


ALL_BLACKLIST = [normalize_mac(mac)
                 for mac
                 in JUNIPER_NON_UNIQUE_MACS + FROM_FIELDS_BLACK_LIST]


def compare_reg_mac(reg_mac, mac):
    if not reg_mac or not mac:
        return False
    if not isinstance(reg_mac, str) or not isinstance(mac, str):
        return False
    if len(reg_mac) != 12 or len(mac) != 12:
        return False
    for i in range(12):
        if reg_mac[i] == '*':
            continue
        if reg_mac[i] != mac[i]:
            return False
    return True


DANGEROUS_IPS = ['1.1.1.1', '8.8.8.8', '2.4.2.4', '8.8.4.4', '1.0.0.1']
