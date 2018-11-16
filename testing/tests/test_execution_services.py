
# pylint: disable=unused-import, redefined-outer-name, too-many-statements, pointless-string-statement, too-many-locals
import time

import dateutil.parser
from services.axonius_service import get_service, BLACKLIST_LABEL
from services.adapters.ad_service import ad_fixture
from services.plugins.general_info_service import general_info_fixture
from services.plugins.pm_status_service import pm_status_fixture
from services.plugins.device_control_service import device_control_fixture
from services.plugins.static_analysis_service import static_analysis_fixture
from test_credentials.test_ad_credentials import ad_client1_details, \
    CLIENT1_DEVICE_ID_BLACKLIST, CLIENT1_DC1_ID
from test_credentials.test_gui_credentials import DEFAULT_USER
from axonius.utils.wait import wait_until

EXECUTION_TIMEOUT = 60 * 50


def test_execution_modules(
        axonius_fixture, ad_fixture, general_info_fixture, pm_status_fixture, device_control_fixture,
        static_analysis_fixture):
    # Step 1, Run a cycle without execution to check how it acts.
    # We set execution to disabled while enabling pm. pm should not work in that case.
    axonius_system = get_service()
    axonius_system.core.set_config(
        {
            'config.execution_settings.enabled': False,
            'config.execution_settings.pm_rpc_enabled': True,
            'config.execution_settings.pm_smb_enabled': True,
        }
    )

    # Delete all devices beforehand.
    axonius_system.get_devices_db().drop()
    axonius_system.get_devices_db_view().drop()
    axonius_system.get_users_db().drop()
    axonius_system.get_users_db_view().drop()

    # Run a cycle.
    ad_fixture.add_client(ad_client1_details)
    axonius_system.scheduler.start_research()
    axonius_system.scheduler.wait_for_scheduler(True)
    wait_until(lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Research Phase Successfully.', 10))

    axonius_system.assert_device_in_db(ad_fixture.unique_name, CLIENT1_DC1_ID)
    axonius_system.assert_device_in_db(ad_fixture.unique_name, CLIENT1_DEVICE_ID_BLACKLIST)

    # Assert general info & pm status are async
    assert general_info_fixture.log_tester.is_str_in_log('Triggered execute unblocked', 5)
    assert pm_status_fixture.log_tester.is_str_in_log('Triggered execute unblocked', 5)

    # Assert general info & pm status do not work when execution is off
    assert general_info_fixture.log_tester.is_str_in_log('Execution is disabled, not continuing', 5)
    assert pm_status_fixture.log_tester.is_str_in_log('Execution is disabled, not continuing', 5)

    # Step 2, Run a cycle with general info & pm status.
    axonius_system.core.set_config(
        {
            'config.execution_settings.enabled': True,
            'config.execution_settings.pm_rpc_enabled': True,
            'config.execution_settings.pm_smb_enabled': True,
        }
    )

    axonius_system.gui.login_user(DEFAULT_USER)
    axonius_system.blacklist_device(ad_fixture.unique_name, CLIENT1_DEVICE_ID_BLACKLIST)

    # Run a research phase and wait for general info and pm status to finish.
    execution_start = time.time()
    axonius_system.scheduler.start_research()
    axonius_system.scheduler.wait_for_scheduler(True)
    wait_until(lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Research Phase Successfully.', 10))

    # Execution takes time. Lets wait for it to finish.
    wait_until(
        lambda: general_info_fixture.log_tester.is_str_in_log(
            'Finished gathering info & associating users for all devices', 10),
        total_timeout=EXECUTION_TIMEOUT - int(time.time() - execution_start)
    )
    wait_until(
        lambda: pm_status_fixture.log_tester.is_str_in_log(
            'Finished gathering pm status', 10),
        total_timeout=EXECUTION_TIMEOUT - int(time.time() - execution_start)
    )

    print(f'Finished execution after {time.time() - execution_start} seconds')
    blacklisted_device = axonius_system.get_device_by_id(ad_fixture.unique_name, CLIENT1_DEVICE_ID_BLACKLIST)[0]
    # Assert we did not run on the blacklisted device. It should have a blacklist label and not have any
    # adapterdata tags.
    blacklist_label_exists = False
    for tag in blacklisted_device['tags']:
        assert tag['type'] != 'adapterdata', f'found unexpected adapterdata tag {tag}'
        if tag['type'] == 'label' and tag['data'] is True and tag['name'] == BLACKLIST_LABEL:
            blacklist_label_exists = True
    assert blacklist_label_exists, 'Did not find a blacklist label!'
    assert general_info_fixture.log_tester.is_str_in_log(
        f'Failure because of blacklist in device {blacklisted_device["internal_axon_id"]}', 100)
    assert pm_status_fixture.log_tester.is_str_in_log(
        f'Failure because of blacklist in device {blacklisted_device["internal_axon_id"]}', 100)

    # Step 3, Run a cycle with execution on but pm set to False.
    # A second discovery cycle also identifies vulnerabilities using the static analyzer regardless if we
    # have execution or not, but we enable here execution just to check that pm doesn't work if execution is on
    # but pm not.
    axonius_system.core.set_config(
        {
            'config.execution_settings.enabled': True,
            'config.execution_settings.pm_rpc_enabled': False,
            'config.execution_settings.pm_smb_enabled': False,
        }
    )
    axonius_system.scheduler.start_research()
    axonius_system.scheduler.wait_for_scheduler(True)
    wait_until(lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Research Phase Successfully.', 10))

    # PM Status should immediately not work.
    assert pm_status_fixture.log_tester.is_str_in_log(
        'PM Status Failure: rpc and smb settings are false (Global Settings)', 5)

    # No need for general info to work. we just wanted it to run in order to see if pm runs as well or not.
    axonius_system.scheduler.stop_research()

    # Check once again the blacklisted device is blacklisted (nothing should have changed)
    blacklisted_device = axonius_system.get_device_by_id(ad_fixture.unique_name, CLIENT1_DEVICE_ID_BLACKLIST)[0]
    blacklist_label_exists = False
    for tag in blacklisted_device['tags']:
        assert tag['type'] != 'adapterdata', f'found unexpected adapterdata tag {tag}'
        if tag['type'] == 'label' and tag['data'] is True and tag['name'] == BLACKLIST_LABEL:
            blacklist_label_exists = True
    assert blacklist_label_exists, 'Did not find a blacklist label!'

    # At this moment we have all devices after general info & pm & static analysis succeeded, we conduct a lot of tests
    # to see that everything was successful. This mainly checks for all data tabs to see that we got a lot of info.

    # First, we check a certain device to see if it has many of the data we want it to have.
    dc1 = axonius_system.get_device_by_id(ad_fixture.unique_name, CLIENT1_DC1_ID)[0]
    dc1_general_info = \
        [tag for tag in dc1['tags'] if tag['plugin_name'] == 'general_info' and tag['type'] == 'adapterdata']
    assert len(dc1_general_info) == 1, 'Expecting exactly 1 general info data tag!'
    dc1_general_info = dc1_general_info[0]['data']

    assert \
        {'admin_name': 'Administrator@TESTDOMAIN', 'admin_type': 'Admin User'} in dc1_general_info['local_admins']
    assert {'admin_name': 'Organization Management@TESTDOMAIN', 'admin_type': 'Group Membership'} in \
        dc1_general_info['local_admins']
    dc1_users = {u['user_sid']: u for u in dc1_general_info['users']}
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']['username'] == 'Administrator@TestDomain.test'
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']['is_local'] is False
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']['origin_unique_adapter_name'] == \
        'active_directory_adapter_0'
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']['origin_unique_adapter_data_id'] == \
        'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test'
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']['origin_unique_adapter_client'] == \
        'TestDomain.test'
    assert 'last_use_date' in dc1_users['S-1-5-21-3246437399-2412088855-2625664447-500']
    assert dc1_users['S-1-5-21-3246437399-2412088855-2625664447-1140'] == \
        {
            'user_sid': 'S-1-5-21-3246437399-2412088855-2625664447-1140',
            'username': 'SM_5f9a36f4ebd642018@TESTDOMAIN',
            'is_local': False,
            'is_disabled': True,
            'origin_unique_adapter_name': 'active_directory_adapter_0',
            'origin_unique_adapter_data_id': 'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test',
            'origin_unique_adapter_client': 'TestDomain.test'}

    assert 'Administrator@TestDomain.test' in dc1_general_info['last_used_users']
    # This is a random number but there is no way we would have less than 10 installed software on any machine
    assert len(dc1_general_info['installed_software']) > 10
    assert {'vendor': 'Microsoft', 'name': 'Office', 'version': '2016'} in dc1_general_info['installed_software']
    assert {'vendor': 'Adobe Systems Incorporated', 'name': 'Adobe Flash Player 30 PPAPI', 'version': '30.0.0.113'} \
        in dc1_general_info['installed_software']
    assert len(dc1_general_info['cpus']) >= 2    # I hope you don't ever downgrade dc1 to have less than 2 cpu's.
    # have at least name, bitness, cores, load_percentage, arch and ghz.
    # The values here change all the time so i can't rely on static values.
    assert len(dc1_general_info['cpus'][0].keys()) >= 6
    assert dc1_general_info['bios_version'] == '6.00'
    assert dc1_general_info['bios_serial'] == 'vmware-56 4d 1b 18 1f 03 86 b3-03 f4 ab 70 a7 c6 95 5a'
    assert dc1_general_info['device_model'] == 'VMware Virtual Platform'
    assert dc1_general_info['device_manufacturer'] == 'VMware, Inc.'
    assert dc1_general_info['hostname'] == 'dc1'
    assert 'total_number_of_physical_processors' and 'total_number_of_cores' in dc1_general_info
    assert dc1_general_info['domain'] == 'TestDomain.test'
    assert dc1_general_info['part_of_domain'] is True
    assert dc1_general_info['pc_type'] == 'Desktop'
    assert dc1_general_info['os'] == \
        {
            'type': 'Windows',
            'distribution': 'Server 2016',
            'install_date': dateutil.parser.parse('2018-04-09 08:49:06'),
            'major': 10,
            'minor': 0,
            'build': '14393'}

    assert 'boot_time' in dc1_general_info
    assert 'total_physical_memory' in dc1_general_info
    assert 'free_physical_memory' in dc1_general_info
    assert 'physical_memory_percentage' in dc1_general_info
    assert 'number_of_processes' in dc1_general_info
    assert len(dc1_general_info['hard_drives']) > 1
    assert {'security_patch_id': 'KB3199986', 'installed_on': dateutil.parser.parse('2016-11-21 00:00:00')} \
        in dc1_general_info['security_patches']
    assert 'time_zone' in dc1_general_info
    assert '00:0C:29:C6:95:5A' in [nic.get('mac') for nic in dc1_general_info['network_interfaces']]
    assert len(dc1_general_info['connected_hardware']) > 5
    assert {'hw_id': 'USB\\VID_0E0F&PID_0003&MI_01\\7&2A63CEAD&0&0001',
            'name': 'USB Input Device',
            'manufacturer': '(Standard system devices)'} in dc1_general_info['connected_hardware']
    assert 'general_info_last_success_execution' in dc1_general_info

    dc1_pm_status = [tag for tag in dc1['tags'] if tag['plugin_name'] == 'pm_status' and tag['type'] == 'adapterdata']
    assert len(dc1_pm_status) == 1, 'Expecting exactly 1 pm status data tag!'
    dc1_pm_status = dc1_pm_status[0]['data']

    assert len(dc1_pm_status['available_security_patches']) > 1
    assert \
        {
            'title': '2018-05 Cumulative Update for Windows Server 2016 for x64-based Systems (KB4103720)',
            'security_bulletin_ids': [],
            'kb_article_ids': [
                '4103720'
            ],
            'patch_type': 'Software',
            'categories': [
                'Updates',
                'Windows Server 2016'
            ],
            'publish_date': dateutil.parser.parse('2018-05-17 00:00:00')
        } in dc1_pm_status['available_security_patches']
    assert 'pm_last_execution_success' in dc1_pm_status

    # Next, we wanna see how many devices have general info and pm status. Note that this condition is true now
    # but might not be true in the future, when general info will run on devices which are not necessarily windows
    # from ad.
    execution_eligible_devices = axonius_system.get_devices_with_condition(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'plugin_name': 'active_directory_adapter',
                            'data.os.type': 'Windows',
                            'data.network_interfaces.ips': {'$exists': True}
                        }
                }
        }
    )

    general_info_success = 0
    pm_status_success = 0
    did_have_hostname_mismatch = False
    did_have_last_logon_not_from_domain = False
    for device in execution_eligible_devices:
        for tag in device['tags']:
            if tag['type'] == 'adapterdata' and tag['plugin_name'] == 'general_info':
                general_info_success += 1
            elif tag['type'] == 'adapterdata' and tag['plugin_name'] == 'pm_status':
                pm_status_success += 1
            elif tag['type'] == 'label' and tag['name'].lower() == 'last logon not from domain' and tag['data'] is True:
                did_have_last_logon_not_from_domain = True
            elif tag['type'] == 'label' and tag['name'].lower() == 'hostname conflict' and tag['data'] is True:
                did_have_hostname_mismatch = True

    assert did_have_last_logon_not_from_domain
    assert did_have_hostname_mismatch

    # Currently we have pretty bad execution statistics, so i wanna validate these small numbers to see
    # that we don't hit something much worse.
    assert general_info_success > len(execution_eligible_devices) / 3
    assert pm_status_success > len(execution_eligible_devices) / 5

    # Check for users
    assert axonius_system.get_users_db_view().find({'specific_data.data.is_local': True}).count() > 10
    assert axonius_system.get_users_db_view().find({'specific_data.data.is_admin': True}).count() > 5
    assert axonius_system.get_users_db_view().find({'specific_data.data.account_disabled': True}).count() > 5
    assert axonius_system.get_users_db_view().find({'specific_data.data.is_locked': True}).count() > 0
    assert axonius_system.get_users_db_view().find({'specific_data.data.password_not_required': True}).count() > 0
    assert axonius_system.get_users_db_view().find(
        {'specific_data.data.last_seen_in_devices': {'$exists': True}}).count() > 5
    assert axonius_system.get_users_db_view().find(
        {'specific_data.data.last_seen_in_devices': {'$exists': True}}).count() > 5
    assert axonius_system.get_users_db_view().find(
        {'specific_data.data.image': {'$exists': True}}).count() > 2

    # Lets get all devices with associated users and see if the users were created and if they have associated devices.
    '''
    associated_devices_and_users = 0
    for device in execution_eligible_devices:
        for tag in device['tags']:
            if tag['type'] == 'adapterdata' and tag['plugin_name'] == 'general_info':
                pass
    '''
