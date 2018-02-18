from enum import Enum, auto

from qcore_adapter.protocol.qtp.common import CStyleEnum


class OperationalCode(Enum):
    EraseMemoryRequest = 1  # Erase memory request
    WriteDataRequest = 2  # Write Data Request
    CompareFileVersionRequest = 3  # Compare File Version Request
    ValidateCrcRequest = 5  # Validate Crc Request
    UploadCompleteNotify = 6  # Upload Complete Notify
    Response = 7  # Response to request
    SetDeployInformation = 8  # Set Deploy information
    WriteResponse = 9  # Write Response


class PackageType(CStyleEnum):
    Software = auto()
    DrugLibrary = auto()
    IvciBarcode = auto()


class UploadResult(CStyleEnum):
    OK = auto()
    HardwareFailure = auto()
    Aborted = auto()
    FileNotAccessible = auto()
