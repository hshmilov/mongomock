DOCKER_PORTS = {
    'gui':                              80,
    'execution':                        4999,
    'aggregator':                       5000,
    'active-directory-adapter':         5001,
    'reports':                          5002,
    'epo-adapter':                      5003,
    'jamf-adapter':                     5004,
    'system-scheduler':                 5005,
    'correlator':                       5009,
    'static-correlator':                5010,
    'dns-conflicts':                    5011,
    'nexpose-adapter':                  5012,
    'csv-adapter':                      5013,
    'qcore-adapter':                    5015,
    'qcore-mediator':                   5016,
    'careful-execution-correlator':     5039,
    'core':                             5050,
    'esx-adapter':                      5111,
    'aws-adapter':                      5112,
    'traiana-lab-machines-adapter':     5113,
    'stresstest-adapter':               5114,
    'bomgar-adapter':                   5115,
    'gotoassist-adapter':               5200,
    'carbonblack-adapter':              5211,
    'puppet-adapter':                   5222,
    'chef-adapter':                     5223,
    'airwatch-adapter':                 5228,
    'nessus-adapter':                   5555,
    'general-info':                     5556,
    'symantec-adapter':                 5676,
    'qualys-adapter':                   5677,
    'sentinelone-adapter':              5678,
    'splunk-symantec-adapter':          5679,
    'splunk-nexpose-adapter':           5681,
    'eset-adapter':                     5682,
    'desktop-central-adapter':          5683,
    'fortigate-adapter':                5689,
    'sccm-adapter':                     5699,
    'forcepoint-csv-adapter':           5770,
    'qualys-scans-adapter':             5777,
    'cisco-adapter':                    6001,
    'minerva-adapter':                  6010,
    'bigfix-adapter':                   6012,
    'ensilo-adapter':                   6013,
    'secdo-adapter':                    6015,
    'mobileiron-adapter':               6016,
    'juniper-adapter':                  6017,
    'openstack-adapter':                6018,
    'mongo':                            27017,
}

assert len(set(DOCKER_PORTS.values())) == len(DOCKER_PORTS)
