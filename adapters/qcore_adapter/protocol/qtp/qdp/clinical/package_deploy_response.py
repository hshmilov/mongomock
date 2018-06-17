import enum

from construct import Struct, Enum, Byte, Int32ul, Pass, Probe
from qcore_adapter.protocol.qtp.common import QcoreString, CStyleEnum, enum_to_mapping
from qcore_adapter.protocol.qtp.qdp.qdp_registration import DeviceVersion
from qcore_adapter.protocol.qtp.qsu.consts import PackageType


class DeployUpdateResponseCodeType(enum.Enum):
    DeploymentRequestQueued = 1  # Queued
    DeploymentRequestPending = 2  # Pending
    DeploymentRequestUpdating = 3  # Updating
    DeploymentRequestComplete = 4  # Complete
    DeploymentRequestCanceled = 5  # Canceled
    DeploymentRequestErrorUnsupported_file = 6  # Error: Unsupported file
    DeploymentRequestErrorInvalid_file = 7  # Error: Invalid file
    DeploymentRequestErrorFile_not_found = 8  # Error: File not found
    DeploymentRequestErrorDeployment_pending = 9  # Error: During Deployment Pending
    DeploymentRequestErrorAlready_deployed = 10  # Error: Already deployed
    DeploymentRequestErrorInvalid_manifest = 11  # Error: Invalid manifest
    DeploymentRequestErrorFailed_download = 12  # Error: Failed download
    DeploymentRequestErrorUnknown = 13  # Error: Uknown
    DeploymentRequestErrorSameSoftwareVersionInstalled = 14  # Error: Same software already installed
    DeploymentRequestPumpIsBusy = 15  # Pump is busy (not turned off)
    DeploymentRequestErrorHardwareFailure = 16  # Error: Hardware failure (when writing/erasing flash memory)
    DeployUpdateResponseCodeTypes = 17  # Convention


class ResourceUpdateStatus(enum.Enum):
    ResourceUpdateSuccessfull = 1
    ResourceUpdateTimeoutError = 2
    ResourceUpdateCrcError = 3
    ResourceUpdateDataFramingError = 4
    ResourceUpdateIncorrectIdError = 5
    ResourceUpdateUnspecifiedError = 6
    ResourceUpdateInvalidDrugLibrary = 7
    ResourceUpdateDlVersionMissmatch = 8
    nResourceUpdateStatuses = 9


PackageDeployResponseMessage = Struct(
    'PackageDeployResponseMessage' / Pass,
    'deployment_data' / QcoreString,
    'package_type' / Enum(Byte, **enum_to_mapping(PackageType)),
    'deploy_update_response_code' / Enum(Byte, **enum_to_mapping(DeployUpdateResponseCodeType)),
    'resource_update_status' / Enum(Byte, **enum_to_mapping(ResourceUpdateStatus)),
    'package_url' / QcoreString,
    'package_version' / DeviceVersion,
    'deployment_manifest_version' / DeviceVersion,

    'file_update_name' / QcoreString,
    'manifest_name' / QcoreString,

    'hash' / QcoreString,
    'hash_algo_type' / QcoreString,
    'device_class' / QcoreString,
    'component_type' / QcoreString,
    'file_type' / QcoreString,
    'valid_date' / Int32ul,
    'force_update' / Byte,
    'manifest_low' / Int32ul,
    'manifest_high' / Int32ul
)
