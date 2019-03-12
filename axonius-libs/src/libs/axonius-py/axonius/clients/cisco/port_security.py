from enum import Enum, auto
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.utils.parsing import format_mac

# pylint: disable=line-too-long


class ViolationAction(Enum):
    shutdown = 1  # the interface will be forced to shut down.
    # the matched traffic will be dropped and cpsSecureMacAddrViolation notification will be generated.
    dropNotify = auto()
    drop = auto()  # the matched traffic will be dropped.


class IfaceStatus(Enum):
    secureup = 1  # This indicates port security is operational.
    # This indicates port security is not operational. This happens when port security is configured to be enabled but could not be enabled due to certain reasons such as conflict with other features.
    securedown = auto()
    shutdown = auto()  # This indicates that the port is shutdown due to port security violation when the object cpsIfViolationAction is of type 'shutdown'."


class SecureMacAddressEntry(SmartJsonClass):
    mac_address = Field(str, 'Mac', converter=format_mac)
    type = Field(str,
                 'Type',
                 description='Indicates if the secure MAC address is a configured (static) or learned (dynamic) address on this interface',
                 enum=['Dynamic', 'Static'])
    remaining_age_time = Field(str,
                               'Remaining Age Time (Minutes)',
                               description='Indicates the remaining age of the secure MAC address if aging is enabled on that port. A value of 0 indicates that aging is disabled for this MAC address entry')


class PortSecurityInterface(SmartJsonClass):
    name = Field(str, 'Interface Name')
    status = Field(IfaceStatus,
                   'Interface Status',
                   description='The operational status of the port security feature on an interface')
    violation_action = Field(str,
                             'Violation Action',
                             description='Determines the action that the device will take if the traffic matches the port security violation')
    entries = ListField(SecureMacAddressEntry,
                        'Entries',
                        description='Entries containing secure MAC address information for the particular interface')
    max_addr = Field(int,
                     'Max Secure Addresses',
                     description='The maximum number (N) of MAC addresses to be secured on the interface')
    sticky = Field(bool,
                   'Sticky',
                   description='Indicates whether sticky port security feature is enabled on this interface')

    violation_count = Field(int,
                            'Violation Count',
                            description='Indicates the number of violations occurred on a secure interface')
