from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping
from enum import auto


class Response(CStyleEnum):
    ResponseEraseOk = auto()  # Erasure OK
    ResponseEraseFailure = auto()  # Erasure Failure
    ResponseWriteOk = auto()  # Writing OK
    ResponseWriteFailure = auto()  # Writing Failure
    ResponseWriteMemoryNotErased = auto()  # Writing to not erased memory
    ResponseVersionDataSame = auto()  # Same Version data
    ResponseVersionDataDifferent = auto()  # Different Version data
    ResponseCrcCorrect = auto()  # Correct CRC
    ResponseCrcWrong = auto()  # Wrong CRC
    ResponseSwUploadFinishAccepted = auto()  # Software upload finish is accepted
    ResponseDrugLibraryUploadFinishAccepted = auto()  # Drug Library upload finish is accepted
    ResponsePumpIsBusy = auto()  # Pump cannot continue update process right now
    ResponseFinishedWithFailureAccepted = auto()  # The update process finished with failure
    ResponseMissingDeployInformation = auto()  # Missing deploy information
    ResponseIvciBarcodeUploadFinishAccepted = auto()  # IVCI barcode finish is accepted
    nResponses = auto()


# QsuResponse.cpp
ResponseMessage = Struct(
    'ResponseMessage' / Pass,
    'response' / Enum(Byte, **enum_to_mapping(Response)),
)
