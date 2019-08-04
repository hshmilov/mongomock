from axonius.utils.parsing import parse_versions_raw

VALID_VERSIONS_DICT = {
    '3.412.23.2': '000000003000004120000002300000002',
    '2.1': '00000000200000001',
    '0.0.231': '0000000000000000000000231',
    '21309238521.21.3980': '0213092380000002100003980',
    '213.1': '00000021300000001',
    '13.0.14500.10': '000000013000000000001450000000010'
}

INVALID_VERSIONS_DICT = {
    'abadfsa': '',
    '    ': '',
    '1:9.10.3.dfsg.P4-8ubuntu1.11': '',
    '12qwerty.19.4': '',
    '!@#$%^&*': '',
    '2:6debian4-1.1.1': '',
    '12..23': '',
    '4::412.5': '',
    '10.0.240.W': '',
    '01/11/2018 1.0.0.146': ''
}

LINUX_SOFTWARE_VERSIONS_DICT = {
    '0.6.40-2ubuntu11.3': '0000000000000000600000040',
    '2.2.52-3': '0000000020000000200000052',
    '3.113+nmu3ubuntu4': '00000000300000113',
    '17.1-27-geb292c18-0ubuntu1~16.04.1': '00000001700000001',
    '2:6.4-1debian1.1': '20000000600000004',
    '2.1.5+deb1+cvs20081104-13.1ubuntu0.16.04.1': '0000000020000000100000005'
}

EDGE_CASE_VERSIONS = {
    '2.13.1.3.657.2.14': '000000002000000130000000100000003000006570000000200000014',
    '4': '000000004',
    '2.1.3 ': '0000000020000000100000003',
    '2.1.3': '0000000020000000100000003',
    '213478432850236.219832573.231705': '0213478432198325700231705'
}


def test_valid_software_versions():
    for original, expected_raw in VALID_VERSIONS_DICT.items():
        assert parse_versions_raw(original) == expected_raw, f'Failed on version {original}'


def test_invalid_software_versions():
    for original, expected_raw in INVALID_VERSIONS_DICT.items():
        assert parse_versions_raw(original) == expected_raw, f'Failed on version {original}'


def test_linux_software_versions():
    # Should return the primary version listen if valid, if not, should return an empty string
    for original, expected_raw in LINUX_SOFTWARE_VERSIONS_DICT.items():
        assert parse_versions_raw(original) == expected_raw, f'Failed on version {original}'


def test_edge_case_versions():
    for original, expected_raw in EDGE_CASE_VERSIONS.items():
        assert parse_versions_raw(original) == expected_raw, f'Failed on version {original}'
