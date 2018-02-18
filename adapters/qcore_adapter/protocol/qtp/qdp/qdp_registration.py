from construct import Struct, Byte, Int32ul, Pass, OneOf

from qcore_adapter.protocol.qtp.common import QcoreString

DeviceVersion = Struct(
    'DeviceVersion' / Pass,
    'major' / Byte,
    'minor' / Byte,
    'build' / Int32ul
)

ResourceInfo = Struct(
    'ResourceInfo' / Pass,
    'name' / QcoreString,
    'timestamp' / Int32ul,
    'version' / QcoreString,
    'schema_version' / QcoreString
)

InfuserInfo = Struct(
    'InfuserInfo' / Pass,
    'infuser_name' / QcoreString,
    'delivery_channels_num' / Int32ul,
    'active_dl' / ResourceInfo,
    'active_lang_pack' / ResourceInfo,
    'active_infuser_sw' / ResourceInfo,
    'active_pmm_sw' / ResourceInfo,
)

PumpComponent = Struct(
    'PumpComponent' / Pass,
    'component_type' / Byte,
    'sw_version' / DeviceVersion,
    'hw_version' / DeviceVersion
)

PumpInfo = Struct(
    'PumpInfo' / Pass,
    'protocol_version' / OneOf(Byte, [145]),
    'timestamp' / Int32ul,
    'device_id' / QcoreString,
    'pump_component' / PumpComponent,
    'infuser_info' / InfuserInfo,
    'last_deployment_status' / Byte
)

RegistrationRequestMessage = Struct(
    'RegistrationRequestMessage' / Pass,
    'pump_info' / PumpInfo
)

RegistrationResponseMessage = Struct(
    'RegistrationResponseMessage' / Pass,
    'registration_response' / Byte,
)
