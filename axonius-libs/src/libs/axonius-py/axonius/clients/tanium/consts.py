import re

DEBUG_SKIP = False
VALUES_SKIP = [
    re.compile(r' file missing$', re.I),
    re.compile(r'\[no results\]', re.I),
    re.compile(r'\[no tags\]', re.I),
    re.compile(r'\[resultscurrentlyunavailable\]', re.I),
    re.compile(r'\[current result unavailable\]', re.I),
    re.compile(r'^\(not set\)$', re.I),
    re.compile(r'\[no matches\]', re.I),
    re.compile(r'\[removed\]', re.I),
    re.compile(r'^can not ', re.I),
    re.compile(r'^error:', re.I),
    re.compile(r'^file permissions scanning not enabled$', re.I),
    re.compile(r'^insufficient free disk space$', re.I),
    re.compile(r'^invalid hash type selected$', re.I),
    re.compile(r'^key/value not found$', re.I),
    re.compile(r'^n/a', re.I),
    re.compile(r'^no .* found in path$', re.I),
    re.compile(r'^no shares$', re.I),
    re.compile(r'^none$', re.I),
    re.compile(r'^not applicable$', re.I),
    re.compile(r'^not available$', re.I),
    re.compile(r'^not enough params to decryptjre', re.I),
    re.compile(r'^not found$', re.I),
    re.compile(r'^not implemented', re.I),
    re.compile(r'^not installed', re.I),
    re.compile(r'^not set$', re.I),
    re.compile(r'^tse-error:', re.I),
    re.compile(r'^uninitialized$', re.I),
    re.compile(r'^unsupported$', re.I),
    re.compile(r'^wtmp$', re.I),
    re.compile(r'file.*does not exist', re.I),
    re.compile(r'file.*not found', re.I),
    re.compile(r'InStr\(strTopPorts', re.I),
    re.compile(r'MicrosoftVBScriptruntimeerror', re.I),
    re.compile(r'must be installed to use this sensor$', re.I),
    re.compile(r'no service pack found', re.I),
    re.compile(r'package not installed$', re.I),
    re.compile(r'taniumexecwrapper', re.I),
    re.compile(r'Thereisnotenoughmemoryavailablenow', re.I),
    re.compile(r'uninitialized - waiting for login', re.I),
    re.compile(r'utilities missing:', re.I),
    re.compile(r'^Could not get results$', re.I),
]
VALUES_EMPTY = [None, '', []]
MAC_RE = '[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$'

YES_VALS = ['true', 'yes', 1, True, '1']
NO_VALS = ['false', 'no', 0, False, '0']
