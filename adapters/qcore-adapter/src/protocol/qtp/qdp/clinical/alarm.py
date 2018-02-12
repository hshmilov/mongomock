from enum import auto

from construct import Struct, Enum, Byte, Embedded, Int16ul, Int32ul

from protocol.qtp.qdp.clinical.sequence import QcoreSequence
from protocol.qtp.common import CStyleEnum, enum_to_mapping

AlarmStateType = Enum(Byte, Active=0, Silenced=1, Cleared=2)
AlarmUrgency = Enum(Byte, Low=0, Medium=1, High=2)


class AlarmCode(CStyleEnum):
    NotDefined = auto()  # Not defined
    WatchDogTimerReset = auto()  # Watch dog timer reset occurs
    BatteryTemperatureOutOfRange = auto()  # Temp. of pump (or environment) is out of range
    EndOfBatteryLife = auto()  # End of battery life span (1year or 500 C/D cycles)
    PME_Error = auto()  # Pumping mechanical error (2, 32, 512)
    InternalCommunicationFailure = auto()  # Internal communication failure
    BatteryUsageError = auto()  # Number of charges is not as in backup, the battery used out of pump
    AirInLineSingleOrFirstAccumulated = auto()  # Big enough air bubble detected
    OutputOcclusion = auto()  # Occlusion during treatment
    LowInputPressure = auto()  # Low input pressure during treatment
    ASNotLoadedOrMisplaced = auto()  # Set misplaced / not loaded - on start / during treatment
    AirDetectorFaulty = auto()  # Air detector out of order (e.g. dirty) Fault for AP 34 only.
    BatteryDepletted = auto()  # Battery level is 3 min before depletion
    LowVoltageForCurrentRate = auto()  # Battery cannot  provide enough voltage to run at rate > 800 ml/h
    TemperatureOutOfRange = auto()  # Temp. of pump (or environment) is out of range
    Reserved1 = auto()  # Reserved
    CommunicationError = auto()  # External communication problem (RS232)
    KeyStuck = auto()  # Activation of (soft & hard) key for more than 4 sec
    WiFiMalfunction = auto()  # WiFi module malfunction
    ChargeError = auto()  # Charger failure (e.g. high temp. of charger)
    TreatmentCompleted = auto()  # Treatment complete (not including KVO)
    DoorOpened = auto()  # Door open  during treatment
    PumpInactiveMoreThan10Minutes = auto()  # Pump is on but not running for more then 10 min.
    BatteryForRateLess800Left30Min = auto()  # Battery 30 min before depletion when rate < 800 ml/h
    CalibrationDueNow = auto()  # Calibration due date has arrived / passed
    # 2 days till end of one year of battery use; or battery has reached 98% of 500 C/D cycles, whichever comes first.
    BatteryLifeExpiresDue2Days = auto()
    CalibrationDue2Days = auto()  # Calibration is due in 2 days (date has not yet arrived)
    UsageOfASExpire = auto()  # A.S. was used for more than 24 hours
    TreatmentNearEnd = auto()  # Treatment near end (10% from end)
    CalibrationDue2Weeks = auto()  # Calibration is due in 2 weeks (but more then 2 days)
    BatteryUsageExpiresDue2Weeks = auto()  # 2 weeks till end of one year of battery use
    SystemCurrentOutOfRange = auto()  # Error is not defined
    PressureSensorFaulty = auto()  # Pressure was not calibrated
    SystemError = auto()  # System Error( Only for technician )
    BatteryNotApproved = auto()  # Battery was not approved by Q-Core
    SoftwareValidationError = auto()  # Software validation failed (one of file does not match the CRC or checksum)
    ExternalWatchDogError = auto()  # Recognized that external watch dog is not installed or failed
    InconsistentFlow = auto()  # Inconsistent flow
    UnknownOcclusion = auto()  # Input vacuum or Output pressure
    AirInLineAccumlatedSecondTime = auto()  # 1 ml of air accumulated
    PME_Alarm = auto()  # Pumping mechanism error (1, 4, 8, 16, 64, 128, 2048, 4096)
    CheckOcclusion = auto()  # Check occlusion
    AirInLineInAirTrap = auto(),  # Air in line when air trap is used
    AirInLineDuringAirVent = auto()  #
    AnnualCertificationFailed = auto()  # Annual certification is failed
    ForceInTooBig = auto()  # Detected FIn to big


AlarmClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'state' / AlarmStateType,
    'urgency' / AlarmUrgency,
    'current_alarm' / Byte,
    'code' / Enum(Int16ul, **enum_to_mapping(AlarmCode)),
    'auto_programming_referece' / Int16ul,
    # for 14.5 and above
    'infusion_id' / Int32ul,
    'infusion_segment_id' / Int32ul
)
