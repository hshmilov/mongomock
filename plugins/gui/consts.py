from enum import Enum, auto


class ChartTypes(Enum):
    """
    Possible phases of the system.
    Currently may be Research, meaning fetch and calculate are running, or Stable, meaning nothing is being changed.
    """
    compare = auto()
    intersect = auto()
