from construct import Struct, Int32ul, Pass, this, Int32sl, Byte, Enum, Probe
from qcore_adapter.protocol.qtp.common import QcoreString, enum_to_mapping
from qcore_adapter.protocol.qtp.qdp.qdp_registration import DeviceVersion
from qcore_adapter.protocol.qtp.qsu.consts import PackageType

# QdpmPackageDeployRequest.cpp
PackageDeployRequestMessage = Struct(
    'PackageDeployRequestMessage' / Pass,
    'device_id' / QcoreString,
    'file_to_update_name' / QcoreString,
    'package_url' / QcoreString,
    'force_update' / Enum(Byte, false=0, true=1),
    'deploy_update_type' / Enum(Byte, **enum_to_mapping(PackageType)),
    'version' / DeviceVersion,
    'deployment_manifest_name' / QcoreString,
    'deplyment_version' / DeviceVersion,
    'deployment_data' / Int32ul,
    'hash' / QcoreString,
    'hash_algo_type' / QcoreString,
    'device_class' / QcoreString,
    'component_type' / QcoreString,
    'file_type' / QcoreString,
    'manifest_low' / Int32ul,
    'manifest_high' / Int32ul,
)
