import re

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

API_URL_PREFIX = 'api'

# API V1
HOSTS_ENDPOINT = 'hosts'
PACKAGES_SUBENDPOINT = 'packages'

# API V2
HOSTS_V2_ENDPOINT = 'v2/hosts'
FACTS_SUBENDPOINT = 'facts'


# Note - we don't expect more than couple of tens of result from subendpoints,
# Red Hat examples uses 99999 for a single page of
# facts - https://github.com/RedHatSatellite/sat6Inventory/blob/master/sat6Inventory.py
# packages - https://github.com/RedHatSatellite/sat6CompareHostPackages/blob/master/sat6CompareHostPackages.py
MAX_SUBENDPOINT_RESULTS = 2000

ATTR_INJECTED_FACTS = 'satellite_facts'
ATTR_INJECTED_PACKAGES = 'satellite_packages'
VERISON_FIELDS_TO_SOFTWARE_NAMES = {
    'augeasversion': 'Augeas',
    'facterversion': 'Facter'
}

RE_FIELD_NET_INTERFACE_EXCEPT_LO = re.compile(r'^net\.interface\.'
                                              r'(?!lo)'  # excpet for "lo" interface
                                              r'(?P<interface_name>[^.]+?)\.'
                                              r'(?P<interface_field>.+?)$', re.MULTILINE)

ASYNC_CHUNKS = 50
HOSTS_CHUNKS = 1000
