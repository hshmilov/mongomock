from collections import namedtuple

AnalysisTypes = namedtuple('AnalysisTypes', ('user_devices_association',
                                             'last_used_user_association',
                                             'virtual_host',
                                             'cve_enrichment'))

JOB_NAMES = AnalysisTypes._fields + ('execute', )
