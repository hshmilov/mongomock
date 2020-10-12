"""
Searches for vulnerable software versions.
"""
import csv
import gzip
import itertools
import json
import logging
import os
import shlex
import subprocess
import threading
from collections import defaultdict

from io import StringIO

import cpe
from static_analysis.nvd_nist import nvd_update

logger = logging.getLogger(f'axonius.{__name__}')

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, 'artifacts')
CPE2CSV_BINARY_PATH = os.path.join(CURRENT_DIR, '..', 'cpe2cve')
MAX_RUNTIME_CPE2CVE = 20 * 60
TMP_SH_FILE_PATH = '/tmp/cve_finder.sh'
CVE_FINDER_SH_FILE_TEMPLATE = '''#!/bin/bash
{cpe2cve_path} -d ' ' -d2 , -o ',' -o2 , -cpe 2 -e 2 -matches 0 -cve 2 {artifacts_path}/*.json.gz << EOF
{cpes}
EOF
'''


class NVDSearcher:
    """
    Loads the NVD artifacts into the memory and parses them.
    """

    def __init__(self):
        """
        Initializes the class. We have to read all artifacts and load them into the memory.
        """
        self.__cve_db = None
        self.__use_lock = threading.RLock()

    def update(self):
        """
        Updates the NVD DB.
        :return:
        """
        try:
            nvd_update.update()
        except Exception:
            logger.exception('Cannot update nvd database, loading what is in the disk')
        self._load_artifacts()

    def _load_artifacts(self):
        """
        Loads all artifacts.
        :return:
        """
        with self.__use_lock:
            # Delete all we have. It might be incorrect
            self.__cve_db = dict()

            # Get all files we can update from
            list_dir = os.listdir(ARTIFACT_FOLDER)
            # We want to load artifacts from the oldest to the newest. sort will order this list in the order we want.
            # e.g. ["modified", "2018", "2015", "2017"].sort() == ["2015", "2017", "2018", "modified"]
            list_dir.sort()
            for file_name in list_dir:
                if file_name.endswith('.json.gz'):
                    full_file_name = os.path.join(ARTIFACT_FOLDER, file_name)
                    try:
                        self._parse_artifact(full_file_name)
                    except Exception:
                        logger.exception(f'Failure parsing artifact {full_file_name}. Moving on')

    @staticmethod
    def _get_software_data(vendor_data):
        multiple_vendors = 'Multiple Vendors'
        multiple_software = 'Multiple Software'

        software_name = None
        vendor_name = None
        try:
            if vendor_data:
                vendor_iter = [(','.join(x.get_vendor()), ','.join(x.get_product())) for x in vendor_data]
                vendor_iter = list(itertools.chain(vendor_iter))
                vendors, names = list(map(set, zip(*vendor_iter)))
                if len(vendors) == 1:
                    vendor_name = vendors.pop()
                else:
                    vendor_name = multiple_vendors

                if len(names) == 1:
                    software_name = names.pop()
                else:
                    software_name = multiple_software

                # optimizations for multiple vendors common cases
                if len(vendor_iter) == 2 and ('linux', 'linux_kernel') in vendor_iter:
                    vendor_name, software_name = ('linux', 'linux_kernel')

                if len(vendor_iter) == 2 and ('google', 'chrome') in vendor_iter:
                    vendor_name, software_name = ('google', 'chrome')

                if len(vendor_iter) == 2 and ('wireshark', 'wireshark') in vendor_iter:
                    vendor_name, software_name = ('wireshark', 'wireshark')

                if len(vendor_iter) == 2 and ('debian', 'debian_linux') in vendor_iter:
                    other = list(filter(lambda item: item != ('debian', 'debian_linux'), vendor_iter))
                    if other:
                        other = other[0]
                    if len(other) == 2 and 'linux' not in other[1] and 'zen' not in other[1]:
                        vendor_name, software_name = other
        except Exception as e:
            logger.exception('Failed to get software data')
        return software_name, vendor_name

    # pylint: disable=too-many-locals, too-many-nested-blocks,too-many-branches,too-many-statements

    def _parse_artifact(self, artifact_path):
        """
        Gets an artifact path (.json.gz file) and parses it
        :param artifact_path: a string indicating the path
        :return:
        """
        with gzip.open(artifact_path, 'r') as json_file:
            cve_dict = json.loads(json_file.read())

        # Now parse all CVE's here. We want to save two DB's, a CVE DB and a Vendor->Product->Version DB.
        for cve_raw in cve_dict['CVE_Items']:
            try:
                cve_id_from_nvd = cve_raw['cve']['CVE_data_meta']['ID']
                cve_description = None

                # Search for the description. we might have a couple of languages.
                for data in cve_raw['cve'].get('description', {}).get('description_data', []):
                    if data['lang'] == 'en':
                        cve_description = data['value']
                        break

                cve_severity_v2 = ((cve_raw.get('impact') or {}).get(
                    'baseMetricV2') or {}).get('severity')

                cve_severity_v3 = (((cve_raw.get('impact') or {}).get(
                    'baseMetricV3') or {}).get('cvssV3') or {}).get('baseSeverity')

                cvss_v2 = (((cve_raw.get('impact') or {}).get('baseMetricV2')
                            or {}).get('cvssV2') or {}).get('baseScore')

                cvss_v3 = (((cve_raw.get('impact') or {}).get('baseMetricV3')
                            or {}).get('cvssV3') or {}).get('baseScore')

                cpe_raw = list(itertools.chain(*[cve.get('cpe_match') for cve in
                                                 ((cve_raw.get('configurations', {}) or {}).get('nodes', {}) or [])
                                                 if isinstance(cve, dict) and 'cpe_match' in cve]))
                cpe_raw_for_vendors_and_software = []
                for cpe_data in cpe_raw:
                    if cpe_data.get('vulnerable') and cpe_data.get('cpe23Uri'):
                        try:
                            cpe_raw_for_vendors_and_software.append(cpe.CPE(cpe_data.get('cpe23Uri')))
                        except Exception:
                            logger.debug(f'Couldn\'t parse CPE {cpe_data}')
                software_name, vendor_name = self._get_software_data(cpe_raw_for_vendors_and_software)

                # Save only what's important
                self.__cve_db[cve_id_from_nvd] = {
                    'id': cve_id_from_nvd,
                    'description': cve_description,
                    'severity_v2': cve_severity_v2,
                    'severity_v3': cve_severity_v3,
                    'cvss_v2': cvss_v2,
                    'cvss_v3': cvss_v3,
                    'software_name': software_name,
                    'software_vendor': vendor_name
                }
            except Exception:
                logger.exception(f'Could not parse CVE {cve_raw}, moving on')

        # Try to free memory
        del cve_dict
        # pylint: enable=too-many-locals, too-many-nested-blocks

    def search_by_cve(self, cve_id_to_search):
        with self.__use_lock:
            if self.__cve_db is None:
                self._load_artifacts()
            if cve_id_to_search:
                try:
                    return self.__cve_db.get(cve_id_to_search)
                except Exception:
                    logger.exception(f'Could not get CVE data for {cve_id_to_search}')
        return None

    def search_vulns(self, softwares):
        cpes = []
        for software in softwares:
            try:
                product_id = next(iter(software))
                details = software[product_id]
                vendor_name, product_name, product_version = details
                # Sanitize our input
                vendor_name = str(vendor_name).strip().lower().replace(':', '')
                product_name = str(product_name).strip().lower().replace(':', '')
                product_version = str(product_version).strip().lower().replace(':', '')

                empty_strings = ['', '0']
                if product_name in empty_strings or product_version in empty_strings:
                    logger.debug(f'Error, got an empty string. '
                                 f'Software details - vendor: {str(vendor_name)} '
                                 f'product {str(product_name)} version {str(product_version)}')
                    continue
                # pylint: disable=simplifiable-if-statement
                if vendor_name == '0':
                    logger.error(f'Error, got vendor name 0')
                    continue

                generated_cpe = f'cpe:/a:{vendor_name}:{product_name}:{product_version}'.lower().\
                    replace(' ', '_').\
                    replace('*', '').\
                    replace('?', ''). \
                    replace(',', '')
                # Removing any unicode chars like ® that my appear
                cpes.append(f'{product_id} {generated_cpe}'.encode('ascii', 'ignore').decode('utf-8'))
            except Exception:
                logger.warning(f'Couldn\'t parse software details: {software}')
                continue
        if not cpes:
            return []
        with self.__use_lock:
            if self.__cve_db is None:
                self._load_artifacts()
            with open(TMP_SH_FILE_PATH, 'w') as fh:
                fh.write(CVE_FINDER_SH_FILE_TEMPLATE.format(cpe2cve_path=os.path.abspath(CPE2CSV_BINARY_PATH),
                                                            artifacts_path=os.path.abspath(ARTIFACT_FOLDER),
                                                            cpes='\n'.join(cpes)))
            os.chmod(TMP_SH_FILE_PATH, 0o777)
            output = subprocess.check_output(TMP_SH_FILE_PATH, timeout=MAX_RUNTIME_CPE2CVE).decode('utf-8')
            os.remove(TMP_SH_FILE_PATH)
            csv_reader = csv.reader(StringIO(output))
            software_to_cve = defaultdict(list)
            for row in csv_reader:
                cve_data = self.__cve_db[row[1]].copy()
                cve_data['matched_cpe'] = [x.split(' ')[1] for x in cpes if x.split(' ')[0] == row[0]]
                software_to_cve[row[0]].append(cve_data)
            return software_to_cve

    def search_vuln(self, vendor_name, product_name, product_version):
        """
        This function checks for the entire cve db to see if we have a match. a match is done, if the vendor name
        in our db is a substring of vendor_name, and, the product name inside our db is a substring of the product name,
        and the version is exactly the version.

        e.g., "Adobe Incorporated Systems", "Adobe Acrobat Reader DC", "15.006.30060" will return a list of all CVE's
        for this product. However we will 'almost' have a few more matches since 'Acrobat Reader' is inside 'Acrobat
        Reader DC' even though its a different product. That is why we require the version to be the same.

        we force the db vendor/product name to be a substring of our input and not vica-versa since usually our input
        is much more detailed. e.g, the vendor of adobe would be "Adobe Incorporated Systems", and the product
        would always include "Adobe" in it (e.g "Adobe Acrobat 2017")

        Do note that we are using the 'affected' field of the nvd dist db, which is not the best solution. The best
        solution would be to parse the 'configuration' because if a cve affects version X "and earlier" we might miss
        that if we are in the earlier. But due to the complicity of searching vulnerabilities and false positives that
        might occur we are not using that (an example of a false positive: Search for "Adobe Acrobat 15.0.0" will
        return a CVE affecting "Adobe Acrobat DC 18.0.0 and earlier". but DC and non-DC are entirely different
        so that's incorrect.

        Edit Sept. 2018: We now allow empty vendor names, since sometimes this information is not visible to us.
        In that case we simply ignore the vendor name.
        :param vendor_name:
        :param product_name:
        :param product_version:
        :return:
        """
        # Sanitize our input
        vendor_name = str(vendor_name).strip().lower()
        product_name = str(product_name).strip().lower()
        product_version = str(product_version).strip().lower()

        empty_strings = ['', '0']
        if product_name in empty_strings or product_version in empty_strings:
            logger.debug(f'Error, got an empty string. '
                         f'Software details - vendor: {str(vendor_name)} '
                         f'product {str(product_name)} version {str(product_version)}')
            return []
        # pylint: disable=simplifiable-if-statement
        if vendor_name == '0':
            logger.error(f'Error, got vendor name 0')
            return []

        with self.__use_lock:
            if self.__cve_db is None:
                self._load_artifacts()
            generated_cpe = f'cpe:/a:{vendor_name}:{product_name}:{product_version}'.lower().\
                replace(' ', '_').\
                replace('*', '').\
                replace('?', '').\
                replace(',', '').\
                encode('ascii', 'ignore').decode('utf-8')
            cmd_to_run = shlex.split(f'/bin/sh -c "echo {generated_cpe} | '
                                     f'{CPE2CSV_BINARY_PATH} -cpe 1 -e 1 -cve 1 {ARTIFACT_FOLDER}/*.json.gz"')
            output = subprocess.check_output(cmd_to_run, timeout=MAX_RUNTIME_CPE2CVE).decode('utf-8')
            return [self.__cve_db[cve] for cve in output.strip().split('\n')] if output else []


if __name__ == '__main__':
    # pylint: disable=invalid-name
    db = NVDSearcher()
    cves = db.search_vuln('Adobe Incorporated Systems', 'Adobe Acrobat Reader DC', '15.006.30060')

    for cve in cves:
        cve_id = cve['id']
        description = cve['description']
        print(f'CVE {cve_id}:\n{description}\n')
    exit(0)
    # pylint: enable=invalid-name
