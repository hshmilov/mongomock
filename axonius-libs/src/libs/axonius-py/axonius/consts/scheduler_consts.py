from enum import Enum, auto

from namedlist import namedlist


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
    Clean_Devices = auto()
    Pre_Correlation = auto()
    Run_Correlations = auto()
    Post_Correlation = auto()
    Run_Queries = auto()
    Save_Historical = auto()


SchedulerState = namedlist('SchedulerState',
                           [
                               ('SubPhase', None),
                               ('SubPhaseStatus', None),
                               ('Phase', Phases.Stable),
                               ('AssociatePluginId', None)],
                           )

RESEARCH_THREAD_ID = 'phase_thread'
