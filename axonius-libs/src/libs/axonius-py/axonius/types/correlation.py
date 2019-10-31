from enum import Enum, auto

from namedlist import namedlist


class CorrelateException(Exception):
    pass


class CorrelationReason(Enum):
    Execution = auto()
    Logic = auto()
    NonexistentDeduction = auto()  # Associativity over a nonexisting entity (a->b and b->c therefore a->c)
    StaticAnalysis = auto()
    UserManualLink = auto()
    ServiceNowCreation = auto()
    LinuxSSHScan = auto()
    ShodanEnrichment = auto()
    CensysEnrichment = auto()
    HaveibeenpwnedEnrichment = auto()
    PortnoxEnrichment = auto()
    DetectedError = auto()


# the reason for these data types is that it allows separation of the code that figures out correlations
# and code that links entities (aggregator) or sends notifications.

# Represent a link that should take place.
#
# associated_adapters  - list of tuple between unique adapter name and id, e.g.
#     (
#         ("aws_adapter_30604", "i-0549ca2d6c2e42a70"),
#         ("esx_adapter_14575", "527f5691-de18-6657-783e-56fd1a5322cd")
#     )
#
# data                        - associated data with this link, e.g. {"reason": "they look the same"}
# reason (CorrelationReason)  - 'Execution' or 'Logic' or whatever else correlators will use
#                               'Logic' means the second part has plugin_unique_name
#                               Anything else means the second part has plugin_name
#                               If this is NOT used by the correlator, rather this is used
#                               by anyone who'se directly calling `link_adapters` - please always
#                               pass plugin_unique_name in `associated_adapters` regardless of the reason

CorrelationResult = namedlist('CorrelationResult',
                              ['associated_adapters', 'data', ('reason', CorrelationReason.Execution)])

# The maximal amount of entities to link at once
MAX_LINK_AMOUNT = 10
