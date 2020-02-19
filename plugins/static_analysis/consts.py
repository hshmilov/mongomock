from collections import namedtuple

AnalysisTypes = namedtuple('AnalysisTypes', ('cve_enrichment',
                                             'user_devices_association',
                                             'last_used_user_association',
                                             'virtual_host'))

JOB_NAMES = AnalysisTypes._fields + ('execute', )
