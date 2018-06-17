from enum import Enum, auto


class Phases(Enum):
    """
    Possible phases of the system.
    Currently may be Research, meaning fetch and calculate are running, or Stable, meaning nothing is being changed.
    """
    Research = auto()
    Stable = auto()


class ResearchPhases(Enum):
    """
    Possible sub-phases of the Research phase, representing stages system goes through before completing the research.
    """
    Fetch_Devices = auto()
    Fetch_Scanners = auto()
    Pre_Correlation = auto()
    Run_Correlations = auto()
    Post_Correlation = auto()
    Clean_Devices = auto()
    Run_Queries = auto()


class StateLevels(Enum):
    """
    Data saved about system's current state including the phase, the sub-phase, if there is one, and its status
    """
    Phase = auto()
    SubPhase = auto()
    SubPhaseStatus = auto()


SCHEDULER_INIT_STATE = {StateLevels.Phase.name: Phases.Stable.name,
                        StateLevels.SubPhase.name: None,
                        StateLevels.SubPhaseStatus.name: None}
RESEARCH_THREAD_ID = 'phase_thread'
