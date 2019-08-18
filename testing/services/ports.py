DOCKER_PORTS = {
    'smtp':                             25,
    'maildiranasaurus':                 26,
    'gui':                              443,
    'mockingbird':                      1443,
    'selenium-hub':                     4444,
    'mongo-slave':                      4455,
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
    'bitdefender-adapter':              5044,
    'core':                             5050,
    'softlayer-adapter':                5090,
    'sophos-adapter':                   5092,
    'blackberry-uem-adapter':           5101,
    'fireeye-hx-adapter':               5102,
    'esx-adapter':                      5111,
    'aws-adapter':                      5112,
    'traiana-lab-machines-adapter':     5113,
    'stresstest-adapter':               5114,
    'bomgar-adapter':                   5115,
    'infinite-sleep-adapter':           5116,
    'service-now-adapter':              5117,
    'crowd-strike-adapter':             5118,
    'stresstest-users-adapter':         5119,
    'claroty-adapter':                  5123,
    'cisco-meraki-adapter':             5130,
    'tenable-io-adapter':               5141,
    'gotoassist-adapter':               5200,
    'cylance-adapter':                  5210,
    'carbonblack-defense-adapter':      5211,
    'carbonblack-protection-adapter':   5212,
    'carbonblack-response-adapter':     5213,
    'aruba-adapter':                    5219,
    'puppet-adapter':                   5222,
    'chef-adapter':                     5223,
    'airwatch-adapter':                 5228,
    'kaseya-adapter':                   5286,
    'nessus-adapter':                   5555,
    'general-info':                     5556,
    'pm-status':                        5557,
    'symantec-adapter':                 5675,
    'symantec-altiris-adapter':         5676,
    'qualys-adapter':                   5677,
    'sentinelone-adapter':              5678,
    'absolute-adapter':                 5680,
    'eset-adapter':                     5682,
    'desktop-central-adapter':          5683,
    'fortigate-adapter':                5689,
    'oracle-vm-adapter':                5694,
    'sccm-adapter':                     5699,
    'forcepoint-csv-adapter':           5770,
    'observeit-adapter':                5773,
    'qualys-scans-adapter':             5777,
    'oracle-cloud-adapter':             5779,
    'splunk-adapter':                   5781,
    'mobi-control-adapter':             5784,
    'infoblox-adapter':                 5794,
    'nessus-csv-adapter':               5796,
    'tanium-adapter':                   5797,
    'deep-security-adapter':            5799,
    'quest-kace-adapter':               5840,
    'mssql-adapter':                    5870,
    'cloudflare-adapter':               5880,
    'selenium-vnc':                     5900,
    'lansweeper-adapter':               5907,
    'portnox':                          5908,
    'cynet-adapter':                    5910,
    'illusive-adapter':                 5911,
    'nmap-adapter':                     5920,
    'cybereason-adapter':               5940,
    'snipeit-adapter':                  5941,
    'saltstack-adapter':                5942,
    'foreman-adapter':                  5943,
    'shodan-adapter':                   5944,
    'checkpoint-r80-adapter':           5948,
    'riverbed-adapter':                 5949,
    'paloalto-panorama-adapter':        5950,
    'samange-adapter':                  5960,
    'sysaid-adapter':                   5990,
    'cisco-adapter':                    6001,
    'zabbix-adapter':                   6005,
    'tripwire-enterprise-adapter':      6007,
    'minerva-adapter':                  6010,
    'bigfix-adapter':                   6012,
    'ensilo-adapter':                   6013,
    'secdo-adapter':                    6015,
    'mobileiron-adapter':               6016,
    'juniper-adapter':                  6017,
    'openstack-adapter':                6018,
    'device-control':                   6019,
    'cisco-prime-adapter':              6020,
    'json-file-adapter':                6021,
    'hyper-v-adapter':                  6022,
    'stresstest-scanner-adapter':       6023,
    'azure-adapter':                    6024,
    'junos-adapter':                    6025,
    'okta-adapter':                     6026,
    'tenable-security-center-adapter':  6027,
    'redseal-adapter':                  6028,
    'google-mdm-adapter':               6029,
    'duo-adapter':                      6030,
    'gce-adapter':                      6031,
    'solarwinds-orion-adapter':         6032,
    'cisco-amp-adapter':                6033,
    'static-users-correlator':          6034,
    'divvycloud-adapter':               6035,
    'azure-ad-adapter':                 6036,
    'static-analysis':                  6037,
    'alibaba-adapter':                  6038,
    'malwarebytes-adapter':             6040,
    'datadog-adapter':                  6041,
    'dropbox-adapter':                  6042,
    'nimbul-adapter':                   6043,
    'ibm-tivoli-taddm-adapter':         6044,
    'clearpass-adapter':                6045,
    'cisco-umbrella-adapter':           6046,
    'linux-ssh-adapter':                6047,
    'proxmox-adapter':                  6048,
    'twistlock-adapter':                6049,
    'logrhythm-adapter':                6050,
    'bluecat-adapter':                  6051,
    'armis-adapter':                    6052,
    'counter-act-adapter':              6053,
    'rumble-adapter':                   6054,
    'diag-w':                           6665,  # reserved
    'diag-l':                           6666,  # reserved
    'code42-adapter':                   6667,
    'dynatrace-adapter':                6668,
    'redcloack-adapter':                6669,
    'cloudpassage-adapter':             6670,
    'redcanary-adapter':                6671,
    'truefort-adapter':                 6672,
    'promisec-adapter':                 6673,
    'symantec-ee-adapter':              6674,
    'cisco-ise-adapter':                6675,
    'device42-adapter':                 6676,
    'webroot-adapter':                  6677,
    'spacewalk-adapter':                6678,
    'opswat-adapter':                   6679,
    'unifi-adapter':                    6680,
    'saltstack-enterprise-adapter':     6681,
    'symantec-cloud-workload-adapter':  6682,
    'alertlogic-adapter':               6683,
    'ca-cmdb-adapter':                  6684,
    'datto-rmm-adapter':                6685,
    'zscaler-adapter':                  6686,
    'reimage-tags-analysis':            6687,
    'heavy-lifting':                    6688,
    'instance-control':                 6689,
    'master-proxy':                     8888,  # reserved
    'ssh-socat':                        9958,
    'office-scan-adapter':              9959,
    'librenms-adapter':                 9960,
    'bitsight-adapter':                 9961,
    'endgame-adapter':                  9962,
    'censys-adapter':                   9963,
    'paloalto-cortex-adapter':          9964,
    'netbox-adapter':                   9965,
    'haveibeenpwned-adapter':           9966,
    'jumpcloud-adapter':                9967,
    'cycognito-adapter':                9968,
    'imperva-dam-adapter':              9969,
    'maas360-adapter':                  9970,
    'cisco-firepower-management-center-adapter': 9971,
    'symantec-sep-cloud-adapter':       9972,
    'f5-icontrol-adapter':              9973,
    'druva-adapter':                    9974,
    'symantec-12-adapter':              9975,
    'kaspersky-sc-adapter':             9976,
    'automox-adapter':                  9977,
    'signalsciences-adapter':           9978,
    'mongo':                            27017,
    'mockingbird-db':                   28017
}
