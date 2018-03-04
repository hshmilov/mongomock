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
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import object
import configparser
import time

from jnpr.space import rest, factory, async


class TestCliConfiglets(object):

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

        cglets = self.space.configuration_management.cli_configlets.get(filter_={'name': 'Set description - Pytest'})
        if len(cglets) > 0:
            cglets[0].delete()

    def test_create_configlet(self):
        cg = factory.make_resource(type_name='configuration_management.cli_configlet',
                                   rest_end_point=self.space)
        param1 = factory.make_resource(type_name='configuration_management.cli_configlet_param',
                                       rest_end_point=self.space)
        param1.parameter = 'PortName'
        param1.display_name = 'Port Name'
        param1.parameter_type = 'Text Field'
        param1.order = 1

        param2 = factory.make_resource(type_name='configuration_management.cli_configlet_param',
                                       rest_end_point=self.space)
        param2.parameter = 'Description'
        param2.display_name = 'Port Description'
        param2.parameter_type = 'Text Field'
        param2.order = 2

        pg1 = factory.make_resource(type_name='configuration_management.cli_configlet_page',
                                    rest_end_point=self.space)
        pg1.cli_text = 'interfaces { $PortName { description "$Description"; } }'
        pg1.pagenumber = 1

        cg.name = 'Set description - Pytest'
        cg.category = 'PythonTest'
        cg.execution_type = 'Single'
        cg.device_family = 'ACX/J/M/MX/T/TX/PTX/EX92xx'
        cg.cli_configlet_params = [param1, param2]
        cg.cli_configlet_pages = [pg1]

        cg = self.space.configuration_management.cli_configlets.post(cg,
                                                                     content_type='application/vnd.net.juniper.space.configuration-management.cli-configlet+xml;version=1;charset=UTF-8')

        assert cg.id > 0

        print("Created <%s, %s>" % (cg.name, cg.category))

    def test_apply_configlet(self):
        cglets = self.space.configuration_management.cli_configlets.get(filter_={'name': 'Set description - Pytest'})
        assert len(cglets) > 0, 'Test configlet not present on Space!'

        devices = self.space.device_management.devices.get(filter_={'deviceFamily': 'junos'})
        assert len(devices) > 0, 'No Junos devices present on Space!'

        task = cglets[0].apply_configlet.post(deviceId=devices[0].key,
                                              parameters={'PortName': 'ge-0/0/0', 'Description': 'PyTest - space-ez'})
        assert task.id > 0

    def test_apply_configlet_from_device_management(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'connectionStatus': 'up',
                     'deviceFamily': 'junos'})
        assert len(devices_list) > 0, "No devices connected!"

        cglets = self.space.configuration_management.cli_configlets.get(filter_={'name': 'Set description - Pytest'})
        assert len(cglets) > 0, "Required configlet not present on Space!"

        d = devices_list[0]

        tm = async.TaskMonitor(self.space, 'test_q')

        try:
            result = d.apply_cli_configlet.post(
                task_monitor=tm,
                configletId=cglets[0].get(attr='key'),
                parameters={'PortName': 'ge-0/0/0', 'Description': 'PyTest - space-ez'}
            )

            from pprint import pprint
            pprint(result)

            assert result.id > 0, "Async cli configlet execution Failed"

            pu = tm.wait_for_task(result.id)
            pprint(pu)

            assert ((pu.state == "DONE" and pu.percentage == 100.0) or
                    (pu.percentage == 100.0 and pu.subTask.state == "DONE"))
        finally:
            tm.delete()

    def test_get_configlets(self):
        cglets = self.space.configuration_management.cli_configlets.get()
        assert len(cglets) > 0, "No cli configlets on Space!"

    """
    def test_get_by_context(self):
        cglets = self.space.configuration_management.cli_configlets.cli_configlets_by_context.post(
                        context='')
        assert len(cglets) >= 0
    """

    def test_get_configlet_details(self):
        cglets = self.space.configuration_management.cli_configlets.get()
        n = len(cglets)
        assert n > 0, "No cli configlets on Space!"

        for cglet in cglets[n - 2: n]:
            time.sleep(5)
            details = cglet.get()
            assert details

    def test_get_configlets_params(self):
        cglets = self.space.configuration_management.cli_configlets.get()
        assert len(cglets) > 0, "No cli configlets on Space!"

        n = len(cglets)
        for cglet in cglets[n - 2: n]:
            params = cglet.cli_configlet_params.get()
            for p in params:
                assert p.parameter
                assert p.order
                assert p['display-name']

                details = p.get()
                assert details
                assert details['parameter-type']

    def test_get_configlets_pages(self):
        cglets = self.space.configuration_management.cli_configlets.get()
        assert len(cglets) > 0, "No cli configlets on Space!"

        n = len(cglets)
        for cglet in cglets[n - 2: n]:
            pages = cglet.cli_configlet_pages.get()
            assert pages
            for p in pages:
                assert p.page_number

                details = p.get()
                assert details
                assert details.content


'''
    def test_delete_configlet(self):
        cglets = self.space.configuration_management.cli_configlets.get(filter_={'name': 'Set description - Pytest'})
        if len(cglets) > 0:
            cglets[0].delete()
'''
