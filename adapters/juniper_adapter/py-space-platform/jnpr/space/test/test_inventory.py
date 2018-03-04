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

from jnpr.space import rest
from jnpr.space import resource


class TestInventory(object):

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

    def test_get_managed_elements(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 0, "Not enough devices on Space"

    def test_get_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) >= 2, "Not enough devices on Space"

        for m in me_list[:1]:
            assert isinstance(m, resource.Resource)
            me_details = m.get()
            assert me_details.device.deviceFamily.text.startswith('junos')

    def test_get_ptps_from_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 1, "Not enough devices on Space"

        for me in me_list[0:1]:
            assert isinstance(me, resource.Resource)
            ptp_ref_list = me.ptps.get()
            assert len(ptp_ref_list) > 0
            for ptp in ptp_ref_list:
                assert ptp.href
                assert ptp.name

    def test_get_eqpt_from_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 1, "Not enough devices on Space"

        for me in me_list[0:1]:
            assert isinstance(me, resource.Resource)
            eh_list = me.equipment_holders.get()
            assert len(eh_list) > 0
            for eh in eh_list:
                assert eh.id
                eh_details = eh.get()
                assert eh_details.name == eh.name
                assert eh_details.equipments

    def test_get_re_from_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 1, "Not enough devices on Space"

        for me in me_list[0:1]:
            re_list = me.routing_engines.get()
            assert len(re_list) > 0
            for re in re_list:
                assert re.id
                re_details = re.get()
                assert re_details.name.text.startswith("Routing Engine")
                assert re_details.installedSerialNumber
                print(type(re_details.name))
                print(type(re_details.installedSerialNumber))

    """
    def test_get_mlsn_from_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 0, "Not enough devices on Space"

        for me in me_list:
            mlsn_list = me.multilayer_subnetworks.get()
            assert len(mlsn_list) > 0
            for mlsn in mlsn_list:
                assert mlsn.id
                mlsn_details = mlsn.get()
                assert mlsn_details.name.text.startswith("mlsns")
                assert mlsn_details.managed_elements.managed_element.id
    """

    def test_get_vlans_from_each_managed_element(self):
        me_list = self.space.managed_domain.managed_elements.get()
        assert len(me_list) > 1, "Not enough devices on Space"

        for me in me_list[0:1]:
            vlans_list = me.vlans.get()
            assert len(vlans_list) > 0
            for vlan in vlans_list:
                assert vlan.id >= 0
