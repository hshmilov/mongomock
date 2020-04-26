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

from jnpr.space import xmlutil
from jnpr.space import rest


class TestDevices(object):

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

    def test_devices_raw_config(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'managedStatus': 'In Sync'})
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list:
            raw = d.configurations.raw.get()
            assert raw is not None
            raw_config = xmlutil.xml2obj(raw.configuration.text)

            assert raw_config.version[:7] == d.OSVersion[:7]

            if hasattr(raw_config, 'groups'):
                for g in raw_config.groups:
                    print("Found config group %s on device %s" % (g.name, d.name))

    def test_devices_raw_config_post(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'managedStatus': 'In Sync'})
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list:
            raw = d.configurations.raw.post(xpaths=['/configuration/version',
                                                    '/configuration/interfaces/interface[starts-with(name, "ge-")]'])

            c = raw.configuration
            if hasattr(c, 'interface'):
                for i in c.interface:
                    print(i.name)
                    assert i.name.pyval.startswith('ge-')
            else:
                print('Device %s has no interfaces' % d.name)

            assert c.version[:7] == d.OSVersion[:7]

    def test_devices_expanded_config(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'managedStatus': 'In Sync'})
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list:
            exp = d.configurations.expanded.get()
            assert exp
            exp_config = xmlutil.xml2obj(exp.configuration.text)

            import pytest
            with pytest.raises(AttributeError):
                assert exp_config.groups is None

            assert exp_config.version[:7] == d.OSVersion[:7]

    def test_devices_expanded_config_post(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'managedStatus': 'In Sync'},
            sortby=['name', 'platform'])
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list:
            exp = d.configurations.expanded.post(xpaths=['/configuration/version',
                                                         '/configuration/interfaces/interface[starts-with(name, "ge-")]'])

            c = exp.configuration
            if hasattr(c, 'interface'):
                for i in c.interface:
                    print(i.name)
                    assert i.name.pyval.startswith('ge-'), \
                        "Intf name %s failed check" % i.name

                    """
                    if isinstance(i.name, str):
                        print(i.name)
                        assert i.name.startswith('ge-'), \
                            "Intf name %s failed check" % i.name
                    else:
                        print(i.name.pyval)
                        assert i.name.pyval.startswith('ge-'), \
                            "Intf name %s failed check" % i.name.data
                    """
            assert c.version[:7] == d.OSVersion[:7]

    def test_devices_configs(self):
        devices_list = self.space.device_management.devices.get(
            filter_={'managedStatus': 'In Sync'})
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list:
            configs = d.configurations.get()
            assert len(configs) == 2
            for c in configs:
                xml_config = c.get()
                xml_config = xmlutil.xml2obj(xml_config.configuration.text)
                assert xml_config.version[:7] == d.OSVersion[:7]

    def test_devices_scripts(self):
        devices_list = self.space.device_management.devices.get()
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list[:1]:
            try:
                scripts = d.associated_scripts.get()
                assert len(scripts) > 0
                for s in scripts:
                    assert s.script_device_association.device_name == d.name
            except Exception:
                pass

    def test_devices_softwares(self):
        devices_list = self.space.device_management.devices.get()
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list[:1]:
            try:
                sws = d.associated_softwares.get()
                assert len(sws) >= 0
            except Exception:
                pass

    def test_devices_change_requests(self):
        devices_list = self.space.device_management.devices.get()
        assert len(devices_list) > 1, "Not enough devices on Space"

        for d in devices_list[:1]:
            crs = d.change_requests.get()
            assert len(crs) >= 0
            for cr in crs:
                assert int(cr.deviceId) == int(d.key)
