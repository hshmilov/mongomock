import glob
import os
import threading

import mongomock
import pytest
import urllib3

from axonius.devices.device_adapter import DeviceAdapter
from axonius.plugin_base import EntityType
from static_analysis.nvd_nist.nvd_search import NVDSearcher
from static_analysis.nvd_nist.nvd_update import (ARTIFACT_FOLDER,
                                                 CURRENT_STATE_FILE)
from static_analysis.service import StaticAnalysisService
from static_analysis.tests import consts

# pylint: disable=protected-access, redefined-outer-name, no-member


@pytest.fixture(scope='module')
def nvd_searcher():
    print('\nSetting up NVD searcher')
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if os.path.isfile(CURRENT_STATE_FILE):
        os.remove(CURRENT_STATE_FILE)
    nvd_searcher = NVDSearcher()
    nvd_searcher.update()
    print('Finished updating NVD searcher')

    yield nvd_searcher

    print('\nCleaning up')
    for nvd_file in glob.glob(f'{ARTIFACT_FOLDER}/*'):
        if nvd_file == 'README.md':
            continue
        try:
            os.remove(nvd_file)
            print(f'Removed {nvd_file}')
        except Exception:
            print(f'Problem removing file {nvd_file}, moving on')
            continue


def mock_mongo(entries):
    """
    Sets up a mock mongo collection for insertion, searching, and filtering
    :param entries:
    :return:
    """
    client = mongomock.MongoClient()
    collection = client.db.collection
    for entry in entries:
        collection.insert(entry)
    return collection


def generate_device(cve, software):
    """
    Generates a device adapter object
    :param cve:
    :param software:
    :return:
    """
    mock_sa = MockStaticAnalysisService(nvd_searcher)
    device = mock_sa.new_device_adapter()
    device.add_vulnerable_software(cve_id=cve)
    device.add_installed_software(vendor_name=software.get('vendor_name'),
                                  product_name=software.get('product_name'),
                                  product_version=software.get('product_version'))
    return device


def list_entry_software(entry):
    """
    Parse an entry (from consts, not db) for its installed software
    :param entry: an entry from the consts file in this testing directory
    :return: a list of installed software names from the entry
    """
    list_of_software = []
    for adapter_data in entry.get('adapters'):
        specific_data = adapter_data.get('data')
        list_of_software += [software.get('name') for software in specific_data.get('installed_software') or []]
    return list_of_software


def list_entry_cves(entry):
    """
    Parse an entry (from consts, not db) for its software cves
    :param entry: an entry from the consts file in this testing directory
    :return: a list of cve ids from the entry
    """
    list_of_cves = []
    for adapter_data in entry.get('adapters'):
        specific_data = adapter_data.get('data')
        list_of_cves += [cve.get('cve_id') for cve in specific_data.get('software_cves') or []]
    return list_of_cves


def get_device_internal_axon_id(device):
    """
    :param device: a device returned from a db search
    :return: the device's internal axon id
    """
    device_id = device.get('id')
    return device_id.split('!')[2]


def test_search_nvd_by_cve(nvd_searcher):
    """
    Tests that searching the NVD is possible, checks that
    the search returns a dict and that it gets the correct CVE
    Also tests that the NVD search throws an exception when
    queried with an invalid CVE (don't want it returning data for
    an invalid CVE)
    :param nvd_searcher:
    :return:
    """
    for valid_cve in consts.VALID_CVES_LIST:
        response = nvd_searcher.search_by_cve(valid_cve)
        assert isinstance(response, dict)
        assert response.get('id') == valid_cve

    for invalid_cve in consts.INVALID_CVES_LIST:
        with pytest.raises(Exception):
            assert nvd_searcher.search_by_cve(invalid_cve)


def test_search_nvd_by_software(nvd_searcher):
    """
    Tests that searching the NVD with software works, checks that
    the search returns a list of CVEs, checks that each entry in the list
    is a dict, checks that the dict has CVE data
    Also tests that the NVD search by software throws an exception
    when queried with invalid (or empty) software
    :param nvd_searcher:
    :return:
    """
    for valid_software in consts.VALID_SOFTWARE_LIST:
        vendor_name = valid_software.get('vendor_name')
        product_name = valid_software.get('product_name')
        product_version = valid_software.get('product_version')
        response = nvd_searcher.search_vuln(vendor_name=vendor_name,
                                            product_name=product_name,
                                            product_version=product_version)
        assert isinstance(response, list)
        for cve in response:
            assert isinstance(cve, dict)
            assert 'CVE' in cve.get('id')

    for invalid_software in consts.INVALID_SOFTWARE_LIST:
        vendor_name = invalid_software.get('vendor_name')
        product_name = invalid_software.get('product_name')
        product_version = invalid_software.get('product_version')
        with pytest.raises(Exception):
            assert nvd_searcher.search_vuln(vendor_name=vendor_name,
                                            product_name=product_name,
                                            product_version=product_version)


def test_wrong_input_variable_type(nvd_searcher):
    """
    Tests that adding a CVE or installed software with the wrong variable type
    (i.e. int, bool) throws an exception
    :param nvd_searcher:
    :return:
    """
    mock_sa = MockStaticAnalysisService(nvd_searcher)

    invalid_type_software_device = mock_sa.new_device_adapter()
    invalid_type_cve_device = mock_sa.new_device_adapter()
    with pytest.raises(Exception):
        assert invalid_type_software_device.add_installed_software(vendor='', name=4, version=True)
        assert invalid_type_cve_device.add_vulnerable_software(cve_id=22)


# Tests above were testing the logic for NVD search and Device
# Adapter functions which are necessary for static analysis but
# not defined in static analysis


# Tests below are for the functions defined in static analysis

# pylint: disable=super-init-not-called
class MockStaticAnalysisService(StaticAnalysisService):
    def __init__(self, nvd_searcher, devices_db=None):
        self.__nvd_lock = threading.Lock()
        self.__nvd_searcher = nvd_searcher
        # pylint: disable=invalid-name
        self._StaticAnalysisService__nvd_searcher = nvd_searcher
        # pylint: enable=invalid-name
        self._entity_adapter_fields = {EntityType.Devices: {'fields_set': set([]),
                                                            'raw_fields_set': set([])}}
        self.plugin_unique_name = 'mock_static'
        self.plugin_name = 'static_analysis'
        self._fetch_empty_vendor_software_vulnerabilites = True
        if devices_db:
            self.devices_db = devices_db

    @staticmethod
    def new_device_adapter():
        return DeviceAdapter(set(), set())
# pylint: enable=super-init-not-called


def test_axonius_mongodb_filtering(nvd_searcher):
    """
    Tests that filtering the db yields the correct devices
    :param nvd_searcher:
    :return:
    """
    # These entries should get enriched
    entries_to_enrich = [consts.ENTRY_SOFTWARE_CVES_ONLY,
                         consts.ENTRY_INSTALLED_SOFTWARE_ONLY,
                         consts.ENTRY_BOTH_CVES_AND_SOFTWARE,
                         consts.ENTRY_WITH_TWO_ADAPTERS_CORRELATED,
                         consts.ENTRY_WITH_ADAPTER_REMOVED_AND_NO_CVES,
                         consts.ENTRY_WITH_ADAPTER_REMOVED_AND_DIFFERENT_CVES]

    # Static analysis should ignore this one because it doesn't have cve and installed software
    entries_to_filter_out = [consts.ENTRY_NEITHER_CVES_NOR_SOFTWARE]
    entries = entries_to_enrich + entries_to_filter_out

    collection = mock_mongo(entries)
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)

    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # The number of returned entries should be the same as the number to enrich, the filter,
    # should exclude the entries to filter out
    # This also tests that there is no duplication when the filtered devices are returned
    assert len(returned_entries) == len(entries_to_enrich)

    # Check that the correct devices were filtered out
    returned_entries_ids = sorted([device['internal_axon_id'] for device in returned_entries])
    expected_entries_ids = sorted([device['internal_axon_id'] for device in entries_to_enrich])
    assert returned_entries_ids == expected_entries_ids


def test_get_cve_data_from_device(nvd_searcher):
    """
    This tests that searching the NVD returns the correct CVEs for any existing
    software CVEs a device might have (does not search based on installed software)
    :param nvd_searcher:
    :return:
    """
    # All entries have existing software CVEs
    entry_a = consts.ENTRY_SOFTWARE_CVES_ONLY
    entry_b = consts.ENTRY_BOTH_CVES_AND_SOFTWARE
    entry_c = consts.ENTRY_WITH_ADAPTER_REMOVED_AND_DIFFERENT_CVES

    # These are the CVEs we expect to see returned from the NVD search
    expected_cve_ids_a = sorted(list_entry_cves(entry_a))
    expected_cve_ids_b = sorted(list_entry_cves(entry_b))
    expected_cve_ids_c = sorted(list_entry_cves(entry_c))

    mock_sa = MockStaticAnalysisService(nvd_searcher)

    # These are the CVEs returned from the NVD for entry A
    returned_data_from_entry_a = list(
        mock_sa._StaticAnalysisService__get_cve_data_from_device(entry_a.get('adapters')[0].get('data')))
    returned_cve_ids_a = sorted([cve.get('id') for cve in returned_data_from_entry_a])

    # These are the CVEs returned from the NVD for entry B
    returned_data_from_entry_b = list(
        mock_sa._StaticAnalysisService__get_cve_data_from_device(entry_b.get('adapters')[0].get('data')))
    returned_cve_ids_b = sorted([cve.get('id') for cve in returned_data_from_entry_b])

    # These are the CVEs returned from the NVD for entry C
    returned_data_from_entry_c = list(
        mock_sa._StaticAnalysisService__get_cve_data_from_device(entry_c.get('adapters')[0].get('data')))
    returned_cve_ids_c = sorted([cve.get('id') for cve in returned_data_from_entry_c])

    # The CVE ids before and after enrichment should be the same
    assert expected_cve_ids_a == returned_cve_ids_a
    assert expected_cve_ids_b == returned_cve_ids_b
    assert expected_cve_ids_c == returned_cve_ids_c


def test_get_cve_data_from_installed_software(nvd_searcher):
    """
    This tests that searching the NVD returns CVEs that match with the device's
    installed software (does not search based on existing software cves)
    :param nvd_searcher:
    :return:
    """
    entry_a = consts.ENTRY_INSTALLED_SOFTWARE_ONLY
    entry_b = consts.ENTRY_BOTH_CVES_AND_SOFTWARE

    # These are the software names we expect to see returned from the NVD search
    expected_software_a = sorted(list_entry_software(entry_a))
    expected_software_b = sorted(list_entry_software(entry_b))

    mock_sa = MockStaticAnalysisService(nvd_searcher)

    # These are the enriched CVEs with software names returned from the NVD for entry A
    returned_data_from_entry_a = list(
        mock_sa._StaticAnalysisService__get_cve_data_from_installed_software(
            entry_a.get('adapters')[0].get('data')))
    returned_software_a = sorted([cve.get('software_name') for cve in returned_data_from_entry_a])

    # These are the enriched CVEs with software names returned from the NVD for entry B
    returned_data_from_entry_b = list(
        mock_sa._StaticAnalysisService__get_cve_data_from_installed_software(
            entry_b.get('adapters')[0].get('data')))
    returned_software_b = sorted([cve.get('software_name') for cve in returned_data_from_entry_b])

    # Each enriched software name should be in the list of the original software names for each entry
    # The enriched software may have the same software name multiple times
    # Some of the original software may not be enriched
    for returned_software_name in returned_software_a:
        assert returned_software_name in expected_software_a

    for returned_software_name in returned_software_b:
        assert returned_software_name in expected_software_b


def test_device_with_cves_only(nvd_searcher):
    """
    Tests that a device in the db with only cves (no installed software) is properly enriched
    :param nvd_searcher:
    :return:
    """
    collection = mock_mongo([consts.ENTRY_SOFTWARE_CVES_ONLY])
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # Filter should get just the one entry
    assert len(returned_entries) == 1

    returned_entry = returned_entries[0]
    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entry)

    assert isinstance(created_device, DeviceAdapter)
    created_device = created_device.to_dict()

    # Check that all the cves in the entry are in the created device
    expected_cves = sorted(list_entry_cves(consts.ENTRY_SOFTWARE_CVES_ONLY))
    returned_cves = sorted([cve.get('cve_id') for cve in created_device.get('software_cves')])
    assert expected_cves == returned_cves

    # Check that each of the cves was actually enriched
    for cve in created_device.get('software_cves'):
        assert cve.get('cve_description')
        assert cve.get('cvss')


def test_device_with_installed_software_only(nvd_searcher):
    """
    Tests that a device in the db with only installed software (no cves) is properly enriched
    :param nvd_searcher:
    :return:
    """
    collection = mock_mongo([consts.ENTRY_INSTALLED_SOFTWARE_ONLY])
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # Filter should get just the one entry
    assert len(returned_entries) == 1

    returned_entry = returned_entries[0]
    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entry)

    assert isinstance(created_device, DeviceAdapter)
    created_device = created_device.to_dict()

    # Check that the installed software we know are in the NVD from the entry are in the created device
    # Not all of the software is found in the NVD which is why the names are hardcoded here
    expected_software_names = sorted({'Wireshark 2.4.0 64-bit',
                                      'Google Chrome',
                                      'Safari',
                                      'Adobe Flash Player 30 PPAPI'})
    returned_software_names = sorted({cve.get('software_name') for cve in created_device.get('software_cves')})
    assert expected_software_names == returned_software_names

    # Check that each of the cves was actually enriched
    for cve in created_device.get('software_cves'):
        assert cve.get('cve_id')
        assert cve.get('cve_description')
        assert cve.get('cvss')
        assert cve.get('software_name')


def test_device_with_cves_and_installed_software(nvd_searcher):
    """
    Tests that a device in the db with both installed software and cves is properly enriched
    :param nvd_searcher:
    :return:
    """
    collection = mock_mongo([consts.ENTRY_BOTH_CVES_AND_SOFTWARE])
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # Filter should get just the one entry
    assert len(returned_entries) == 1

    returned_entry = returned_entries[0]
    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entry)

    assert isinstance(created_device, DeviceAdapter)
    created_device = created_device.to_dict()

    # Not all of the software is found in the NVD which is why the names are hardcoded here
    expected_cves = set(list_entry_cves(consts.ENTRY_BOTH_CVES_AND_SOFTWARE))
    expected_software_names = {'Adobe Flash Player 30 PPAPI', 'Safari'}

    returned_cves = {cve.get('cve_id') for cve in created_device.get('software_cves')}
    returned_software_names = {cve.get('software_name') for cve in created_device.get('software_cves')}

    # Check that the cves and software we expect to see returned are subsets
    # of the cves and software actually returned
    assert expected_cves <= returned_cves
    assert expected_software_names <= returned_software_names

    # Check that each of the cves was actually enriched
    for cve in created_device.get('software_cves'):
        assert cve.get('cve_id')
        assert cve.get('cve_description')
        assert cve.get('cvss')


def test_device_with_two_adapters_correlated(nvd_searcher):
    """
    Test that a device with two adapters correlated to it, each of which
    report cves and/or installed software, is enriched properly
    :param nvd_searcher:
    :return:
    """
    collection = mock_mongo([consts.ENTRY_WITH_TWO_ADAPTERS_CORRELATED])
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # Filter should get just the one entry
    assert len(returned_entries) == 1

    returned_entry = returned_entries[0]
    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entry)

    assert isinstance(created_device, DeviceAdapter)
    created_device = created_device.to_dict()

    # Only the first adapter has software cves
    expected_cves = set(list_entry_cves(consts.ENTRY_WITH_TWO_ADAPTERS_CORRELATED))
    # Only the second adapter has installed software
    expected_software_names = {'Wireshark 2.4.0 64-bit', 'Safari', 'Adobe Flash Player 30 PPAPI'}

    returned_cves = {cve.get('cve_id') for cve in created_device.get('software_cves')}
    returned_software_names = {cve.get('software_name') for cve in created_device.get('software_cves')}

    # We should see both the cves from the original cves and the cves from the installed
    # software in the created device
    assert expected_cves <= returned_cves
    assert expected_software_names <= returned_software_names

    # Check that each of the cves was actually enriched
    for cve in created_device.get('software_cves'):
        assert cve.get('cve_id')
        assert cve.get('cve_description')
        assert cve.get('cvss')


def test_device_adapter_removed_and_different_cves(nvd_searcher):
    """
    Tests that a device which was previously enriched, but now has different cves,
    is enriched with the new cves and the old ones are removed
    :param nvd_searcher:
    :return:
    """
    collection = mock_mongo([consts.ENTRY_WITH_ADAPTER_REMOVED_AND_DIFFERENT_CVES])
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    # These cves are from a prior enrichment and should be removed from the device
    outdated_cves = set([])
    for tag in consts.ENTRY_WITH_ADAPTER_REMOVED_AND_DIFFERENT_CVES.get('tags'):
        cves = tag.get('data').get('software_cves')
        for cve in cves:
            outdated_cves.add(cve.get('cve_id'))

    # Filter should get just the one entry
    assert len(returned_entries) == 1

    returned_entry = returned_entries[0]
    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entry)

    assert isinstance(created_device, DeviceAdapter)
    created_device = created_device.to_dict()

    expected_cves = set(list_entry_cves(consts.ENTRY_WITH_TWO_ADAPTERS_CORRELATED))
    returned_cves = {cve.get('cve_id') for cve in created_device.get('software_cves')}

    # Check that the new cves are included in the enriched device
    assert expected_cves <= returned_cves
    # Check that the old cves are no longer included in the enriched device
    assert not outdated_cves & returned_cves

    # Check that each of the cves was actually enriched
    for cve in created_device.get('software_cves'):
        assert cve.get('cve_id')
        assert cve.get('cve_description')
        assert cve.get('cvss')


def test_device_adapter_removed_and_no_cves(nvd_searcher):
    """
    Tests that a device with enriched cves from a previous static analysis run
    that are no longer reported by an adapter on the device are removed
    :param nvd_searcher:
    :return:
    """
    entries = [consts.ENTRY_WITH_ADAPTER_REMOVED_AND_NO_CVES]
    collection = mock_mongo(entries)
    mock_sa = MockStaticAnalysisService(nvd_searcher, collection)
    returned_entries = list(mock_sa._StaticAnalysisService__get_devices_with_software_or_cves())

    created_device = mock_sa.create_device_with_enriched_cves(device=returned_entries[0])

    # A device should still be created since this entry was included in the list of
    # entries to analyze by the db filtering
    assert isinstance(created_device, DeviceAdapter)

    # However, the device's software_cves field should be empty since no adapter
    # reports a cve or installed software
    assert not created_device.to_dict().get('software_cves')

# pylint: enable=protected-access, redefined-outer-name
