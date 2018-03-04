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
from builtins import range
from builtins import object
import configparser
import pytest

from jnpr.space import rest, factory


class TestLogin(object):

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
        self.space = rest.Space(url, user, passwd, use_session=True)

    def test_create_user(self):
        rls = self.space.user_management.roles.get()
        assert len(rls) > 0

        r = factory.make_resource(type_name='user_management.role',
                                  rest_end_point=self.space)
        r.href = rls[0].href

        u = factory.make_resource(type_name='user_management.user',
                                  rest_end_point=self.space)
        u.name = 'space_ez1'
        u.firstName = 'Space'
        u.lastName = 'EZ'
        u.password = '123Juniper'
        u.primaryEmail = 'space_ez@juniper.net'
        u.roles = [r]
        u.read_only = False

        u = self.space.user_management.users.post(u)
        assert u.id > 0

        rls = u.roles.get()
        assert rls[0].href == r.href

    def test_logout_1(self):
        self.space.logout()
        with pytest.raises(Exception):
            self.space.user_management.users.get(filter_={'name': 'super'})

    def test_login(self):
        self.space.login()

    def test_change_password(self):
        us = self.space.user_management.users.get(filter_={'name': 'space_ez1'})
        assert len(us) == 1
        pwd = us[0].change_password.post(
            oldPassword='123Juniper',
            newPassword='456Juniper')
        assert pwd.newPassword == '456Juniper'

    def test_get_user_active_sessions(self):
        us = self.space.user_management.users.get(filter_={'name': 'super'})
        assert len(us) == 1
        ss = us[0].active_user_sessions.get()
        assert len(ss) >= 0

    def test_delete_user(self):
        us = self.space.user_management.users.get(filter_={'name': 'space_ez1'})
        assert len(us) == 1
        us[0].delete()

    def test_logout(self):
        self.space.logout()
        with pytest.raises(Exception):
            self.space.user_management.users.get(filter_={'name': 'super'})

    def test_login_logout_loop(self):
        for _ in range(1, 10):
            self.space.login()
            users_list = self.space.user_management.users.get()
            assert len(users_list) > 0
            self.space.logout()
            with pytest.raises(Exception):
                self.space.user_management.users.get()
