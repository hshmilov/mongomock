import io

from axonius.consts.system_consts import CUSTOMER_CONF_PATH
from test_helpers.machines import PROXY_PORT, PROXY_IP
from ui_tests.tests.instances_test_base import TestInstancesBase

CUSTOMER_CONF = '''
{
  "exclude-list": {
    "add-to-exclude": [
      "nessus",
      "carbonblack_defense",
      "minerva",
      "desktop_central",
      "tenable_io",
      "clearpass",
      "device42",
      "symantec_cloud_workload",
      "cisco_meraki",
      "paloalto_panorama",
      "infinite_sleep",
      "openstack",
      "quest_kace",
      "alibaba",
      "tripwire_enterprise",
      "jamf",
      "azure",
      "cisco_prime",
      "observeit",
      "alertlogic",
      "lansweeper",
      "nmap",
      "duo",
      "unifi",
      "promisec",
      "symantec_ee",
      "proxmox",
      "kaseya",
      "aws",
      "mssql",
      "blackberry_uem",
      "azure_ad",
      "aruba",
      "gotoassist",
      "cynet",
      "riverbed",
      "sentinelone",
      "ibm_tivoli_taddm",
      "okta",
      "chef",
      "redseal",
      "armis",
      "qualys_scans",
      "truefort",
      "illusive",
      "fireeye_hx",
      "traiana_lab_machines",
      "malwarebytes",
      "sccm",
      "twistlock",
      "linux_ssh",
      "cybereason",
      "foreman",
      "esx",
      "bluecat",
      "bomgar",
      "checkpoint_r80",
      "junos",
      "fortigate",
      "juniper",
      "nimbul",
      "infoblox",
      "epo",
      "google_mdm",
      "mobi_control",
      "cisco_amp",
      "dynatrace",
      "logrhythm",
      "deep_security",
      "absolute",
      "carbonblack_response",
      "forcepoint_csv",
      "sophos",
      "zabbix",
      "mobileiron",
      "cisco_umbrella",
      "tenable_security_center",
      "saltstack_enterprise",
      "cloudflare",
      "json_file",
      "stresstest",
      "softlayer",
      "opswat",
      "saltstack",
      "counter_act",
      "qcore",
      "splunk",
      "divvycloud",
      "airwatch",
      "cylance",
      "redcloack",
      "cisco_ise",
      "dropbox",
      "spacewalk",
      "carbonblack_protection",
      "oracle_vm",
      "redcanary",
      "stresstest_scanner",
      "eset",
      "ensilo",
      "service_now",
      "puppet",
      "code42",
      "hyper_v",
      "gce",
      "csv",
      "snipeit",
      "sysaid",
      "oracle_cloud",
      "nessus_csv",
      "claroty",
      "symantec",
      "stresstest_users",
      "datadog",
      "symantec_altiris",
      "tanium",
      "crowd_strike",
      "bigfix",
      "shodan",
      "cisco",
      "cloudpassage",
      "webroot",
      "samange",
      "bitdefender",
      "secdo"
    ],
    "remove-from-exclude": []
  }
}
'''


class TestInstancesUpgrade(TestInstancesBase):

    def test_instances_upgrade(self):
        # faster install
        instance = self._instances[0]
        instance.put_file(file_object=io.StringIO(CUSTOMER_CONF),
                          remote_file_path=str(CUSTOMER_CONF_PATH))
        self.join_node()

        # upgrade
        self.check_upgrade()

    def check_upgrade(self):
        self.logger.info('Starting an upgrade')
        self.run_upgrade_on_node()
        self.logger.info('Upgrade finished')
        self._delete_nexpose_adapter_and_data()
        self._add_nexpose_adadpter_and_discover_devices()

    def run_upgrade_on_node(self):
        instance = self._instances[0]
        upgrade_script_path = '/home/ubuntu/upgrade.sh'
        upgrader = io.StringIO('#!/bin/bash\n'
                               'set -e\n'
                               'cd /home/ubuntu/\n'
                               f'export https_proxy=https://{PROXY_IP}:{PROXY_PORT}\n'  # bypass internet disconnect!
                               'wget https://s3.us-east-2.amazonaws.com/axonius-releases/latest/axonius_latest.py\n'
                               f'echo {instance.ssh_pass} | sudo -S python3 axonius_latest.py\n')

        instance.put_file(file_object=upgrader,
                          remote_file_path=upgrade_script_path)

        rc, out = instance.ssh(f'bash {upgrade_script_path}')
        if rc != 0:
            self.logger.info(f'ERROR: FAILED TO UPGRADE {out}')
        assert rc == 0
