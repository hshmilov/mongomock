#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2015 Juniper Networks, Inc.
# All rights reserved.
#
# Use is subject to license terms.
#
# Licensed under the Apache License, Version 2.0 (the ?License?); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import configparser
import time

from jnpr.space import rest, factory, async


class TestConfigTemplates(object):

    def setup_class(self):
        # Extract Space URL, userid, password from config file
        config = configparser.RawConfigParser()
        import os
        config.read(os.path.dirname(os.path.realpath(__file__)) +
                    "/test.conf")
        url = config.get('space', 'url')
        user = config.get('space', 'user')
        passwd = config.get('space', 'passwd')

        # Create a Space REST end point
        self.space = rest.Space(url, user, passwd)

    def test_create_quick_template(self):
        t = factory.make_resource(type_name='config_template_management.config_template',
                                  rest_end_point=self.space)
        t.name = 'Space_EZ_Test_Quick_Template_3'
        t.description = 'Quick Template for testing from space-ez'
        t.device_family = 'junos'
        t.os_version = '12.3R1.7'  # Crap: Some value must be given! Otherwise it throws exception!

        t = self.space.config_template_management.config_templates.post(
            t,
            xml_name='config-template-no-definition',
            content_type='application/vnd.net.juniper.space.config-template-management.config-template-no-definition+xml;version=1;charset=UTF-8',
            accept='application/vnd.net.juniper.space.config-template-management.config-template-no-definition+xml;version=1')
        assert t.id > 0

        time.sleep(10)
        CLI_DATA = "set interfaces $(interface) description $(description)"
        result = t.configuration.post(clis=CLI_DATA)
        assert result.status == 'SUCCESS'

    """
    def test_create_config_template(self):
        tds = self.space.config_template_management.config_template_definitions.get(
                    filter_={'name': 'Default Syslog Config_JUNOS'})
        assert len(tds) == 1

        t = factory.make_resource(type_name='config_template_management.config_template',
                                        rest_end_point=self.space)
        t.config_template_definition = {'href': tds[0].href}
        t.name = 'Test_Template_1'
        t.description = 'Template for testing from space-ez'

        t = self.space.config_template_management.config_templates.post(t)
        assert t.id > 0
    """

    def test_get_template_configuration(self):
        cts = self.space.config_template_management.config_templates.get()
        assert len(cts) > 0, 'No config template present on Space!'

        for ct in cts:
            if ct.config_type == 'QUICK_TEMPLATE':
                config = ct.configuration.get()
                assert config

    def test_deploy_test_template(self):
        cts = self.space.config_template_management.config_templates.get(
            filter_={'name': 'Space_EZ_Test_Quick_Template_3'})
        assert len(cts) > 0, 'Test config template not present on Space!'

        devices = self.space.device_management.devices.get(filter_={'deviceFamily': 'junos',
                                                                    'connectionStatus': 'up',
                                                                    'managedStatus': 'In Sync'})
        assert len(devices) > 1, 'Not enough connected devices present on Space!'

        tm = async.TaskMonitor(self.space, 'test_ct_deploy_q')

        try:
            task = cts[0].exec_deploy.post(
                task_monitor=tm,
                devices=devices[:2],
                resolved_variables={devices[0].key: {'interface': 'ge-0/0/0', 'description': '1: Set from space-ez pytest'},
                                    devices[1].key: {'interface': 'ge-0/0/0', 'description': '2: Set from space-ez pytest'}})
            assert task.id > 0

            pu = tm.wait_for_task(task.id)

            assert pu
        finally:
            tm.delete()

    def test_audit_test_template(self):
        tm = async.TaskMonitor(self.space, 'test_ct_audit_q')
        cts = self.space.config_template_management.config_templates.get(
            filter_={'name': 'Space_EZ_Test_Quick_Template_3'})
        assert len(cts) > 0, 'Test config template not present on Space!'

        try:
            task = cts[0].exec_audit.post(task_monitor=tm)
            assert task.id > 0
            pu = tm.wait_for_task(task.id)
            assert pu
        finally:
            tm.delete()

    def test_undeploy_test_template(self):
        tm = async.TaskMonitor(self.space, 'test_ct_undeploy_q')
        cts = self.space.config_template_management.config_templates.get(
            filter_={'name': 'Space_EZ_Test_Quick_Template_3'})
        assert len(cts) > 0, 'Test config template not present on Space!'

        assocs = cts[0].device_associations.get()
        devices = []
        for d in assocs['device-association']:
            devices.append(d.device)

        try:
            task = cts[0].exec_undeploy.post(task_monitor=tm,
                                             devices=devices)
            assert task.id > 0
            pu = tm.wait_for_task(task.id)
            assert pu
        finally:
            tm.delete()

    def test_delete_test_template(self):
        cts = self.space.config_template_management.config_templates.get(
            filter_={'name': 'Space_EZ_Test_Quick_Template_3'})
        assert len(cts) > 0, 'Test config template not present on Space!'

        cts[0].delete()

    def test_get_definitions(self):
        defs = self.space.config_template_management.config_template_definitions.get()
        assert len(defs) > 0

        for d in defs:
            details = d.get()
            assert details.state

            # config = d.configuration.get()
            # assert config.data
