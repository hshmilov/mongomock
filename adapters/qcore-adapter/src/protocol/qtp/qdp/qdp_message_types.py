from enum import Enum

from protocol.qtp.common import enum_to_mapping


class QdpMessageTypes(Enum):
    # Refer to QdpMessage.h
    RegistrationMessage = 1
    RegistrationResponse = 2
    DeviceUpdate = 3
    TimeSync = 4
    FileDeploymentRequest = 5
    FileDeploymentResponse = 6
    FileDeploymentComplete = 7
    FileDeploymentInquiryRequest = 8
    DeviceNotify = 9

    # OpCodes 10-20 reserved to Clinical Status Messages
    ClinicalStatusConnectivityUpdate = 10
    ClinicalStatusPowerUpdate = 11
    ClinicalStatusInfusionUpdate = 12
    ClinicalStatusCommandResponseUpdate = 13
    ClinicalStatusRulesetViolationUpdate = 14
    ClinicalStatusAlarmUpdate_wInfusion = 15
    ClinicalStatusAlarmUpdate_woInfusion = 16
    ClinicalStatusSystemUpdate = 17
    ClinicalStatusCcaUpdate = 18

    AutoProgramingRequest = 21
    FileDeploymentRestart = 22

    ConnectionEstablished = 50  # 0x32
    ConnectionLost = 51
    ConnectionFailed = 52
    Warning = 53

    LogDownloadRequest = 60
    LogDownloadResponse = 61

    DebugMessage = 62


QdpMessageTypesReverseMapping = enum_to_mapping(QdpMessageTypes)
