import re

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

REQUIRED_PERMISSIONS = ['view_hosts']
ATTR_INJECTED_FACTS = 'satellite_facts'

VERISON_FIELDS_TO_SOFTWARE_NAMES = {
    'augeasversion': 'Augeas',
    'facterversion': 'Facter'
}

RE_FIELD_NET_INTERFACE_EXCEPT_LO = re.compile(r'^net\.interface\.'
                                              r'(?!lo)'  # excpet for "lo" interface
                                              r'(?P<interface_name>[^.]+?)\.'
                                              r'(?P<interface_field>.+?)$', re.MULTILINE)
