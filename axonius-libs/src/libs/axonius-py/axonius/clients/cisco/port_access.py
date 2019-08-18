from enum import Enum
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field

# pylint: disable=line-too-long,invalid-name


class cpaePortMode(Enum):
    singleHost = 1  # port allows one host to connect and authenticate.
    # port allows multiple hosts to connect.  Once a host is authenticated, all remaining hosts are also authorized.
    multiHost = 2
    multiAuth = 3  # port allows multiple hosts to connect and each host is authenticated.
    other = 4      # none of the above. This is a read-only value which can not be used in set operation.


class cpaePortOperVlanType(Enum):
    """ The type of the Vlan which is assigned to this port
        via IEEE-802.1x and related methods of authentication
        supported by the system.

        A value of 'other' for this object indicates type of
        Vlan assigned to this port; via IEEE-802.1x
        authentication; is other than the ones specified by
        listed enumerations for this object.

        A value of 'none' for this object indicates that there
        is no Vlan assigned to this port via IEEE-802.1x
        authentication.  For such a case, corresponding value
        of cpaePortOperVlan object will be zero.

        A value of 'guest' for this object indicates that Vlan
        assigned to this port; via IEEE-802.1x authentication;
        is of type Guest Vlan and specified by the object
        cpaeGuestVlanNumber for this entry.

        A value of 'authFail' for this object indicates that
        Vlan assigned to this port; via IEEE-802.1x
        authentication; is of type Auth-Fail Vlan and
        specified by the object cpaePortAuthFailVlan for
        this entry."
    """
    other = 1
    operational = 2
    guest = 3
    authFail = 4


class PortAccessEntity(SmartJsonClass):
    name = Field(str, 'Interface Name')
    port_mode = Field(str, 'Port Mode', enum=cpaePortMode)
    operation_vlan_type = Field(int, 'Port Type', enum=cpaePortOperVlanType)
    guest_vlan_number = Field(int, 'Guest Vlan', description='Specifies the Guest Vlan of the interface.  An interface with cpaePortMode value of \'singleHost\' will be moved to its Guest Vlan if the supplicant on the interface is not capable of IEEE-802.1x authentication.  A value of zero for this object indicates no Guest Vlan configured for the interface.')
    auth_fail_vlan_number = Field(int, 'Auth Failed vlan', description='Specifies the Auth-Fail (Authentication Fail) Vlan of the port.  A port is moved to Auth-Fail Vlan if the supplicant which support IEEE-802.1x authentication is unsuccessfully authenticated. A value of zero for this object indicates no Auth-Fail Vlan configured for the port.')
    operation_vlan_number = Field(int, 'Operational vlan', description='The VlanIndex of the Vlan which is assigned to this port via IEEE-802.1x and related methods of authentication supported by the system.  A value of zero for this object indicates that no Vlan is assigned to this port via IEEE-802.1x authentication.')
    shutdown_timeout_enabled = Field(bool, 'Shutdown Timeout Enabled',
                                     description='Specifies whether shutdown timeout feature is enabled on the interface.')
    auth_fail_max_attempts = Field(
        int, 'Auth Fail Max Attempts', description='Specifies the maximum number of authentication attempts should be made before the port is moved into the Auth-Fail Vlan.')
