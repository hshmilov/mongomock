from qcore_adapter.protocol.qtp.common import CStyleEnum
from enum import auto, Enum


class InfusionEvent(CStyleEnum):
    Started = auto()
    Completed = auto()
    Stopped = auto()
    Paused = auto()
    Paused_Automatically = auto()
    Paused_Manualy = auto()
    Paused_Bolus = auto()
    Resumed = auto()
    Resumed_From_Bolus = auto()
    NearEnd = auto()
    Kvo_Started = auto()
    Kvo_Finished = auto()
    BolusStarted = auto()
    BolusFinished = auto()
    Stopped_by_User = auto()
    # placeholder for cleared
    Titration = auto()
    PrimingStarted = auto()
    PrimingStopped = auto()
    DelayStart = auto()
    DelayEnd = auto()
    NewStep = auto()
    StandByStarted = auto()
    StandByStopped = auto()
    NewPatient = auto()
    VolumeCountersCleared = auto()
    Canceled = auto()
    SecondaryFinished = auto()
    StepEnded = auto()
    Rejected = auto()
    InufsionStopped = auto()
    PreStart = auto()
    SamePatient = auto()
    AboutToTitrate = auto()
    InfusionCompleteStarted = auto()
    InfusionCompleteEnded = auto()
    NotDocumented = auto()


InfusionEvent.Cleared = InfusionEvent.Stopped_by_User
