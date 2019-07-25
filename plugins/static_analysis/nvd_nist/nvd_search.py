"""
Searches for vulnerable software versions.
"""
import os
import json
import zipfile
import logging
import threading
import requests.exceptions
from axonius.utils.parsing import get_exception_string
from static_analysis.nvd_nist import nvd_update

logger = logging.getLogger(f'axonius.{__name__}')

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, 'artifacts')


class NVDSearcher:
    """
    Loads the NVD artifacts into the memory and parses them.
    """

    def __init__(self):
        """
        Initializes the class. We have to read all artifacts and load them into the memory.
        """
        self.__cve_db = dict()
        self.__products_db = dict()
        self.__use_lock = threading.Lock()

        # Just load artifacts
        self._load_artifacts()

    def update(self):
        """
        Updates the NVD DB.
        :return:
        """
        try:
            nvd_update.update()
        except requests.exceptions.RequestException:
            logger.warning(f'Warning, Internet problem. moving on: {get_exception_string()}')
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
            self.__products_db = dict()

            # Get all files we can update from
            list_dir = os.listdir(ARTIFACT_FOLDER)
            # We want to load artifacts from the oldest to the newest. sort will order this list in the order we want.
            # e.g. ["modified", "2018", "2015", "2017"].sort() == ["2015", "2017", "2018", "modified"]
            list_dir.sort()
            for file_name in list_dir:
                if file_name.endswith('.json.zip'):
                    full_file_name = os.path.join(ARTIFACT_FOLDER, file_name)
                    try:
                        self._parse_artifact(full_file_name)
                    except Exception:
                        logger.exception(f'Failure parsing artifact {full_file_name}. Moving on')

    # pylint: disable=too-many-locals, too-many-nested-blocks
    def _parse_artifact(self, artifact_path):
        """
        Gets an artifact path (.json.zip file) and parses it
        :param artifact_path: a string indicating the path
        :return:
        """
        archive = zipfile.ZipFile(artifact_path, 'r')
        with archive.open(archive.namelist()[0]) as json_file:
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

                cve_references = [x.get('url') for x in cve_raw['cve'].get(
                    'references', {}).get('reference_data', []) if x.get('url') is not None]

                cve_severity_v2 = ((cve_raw.get('impact') or {}).get(
                    'baseMetricV2') or {}).get('severity')

                cve_severity_v3 = (((cve_raw.get('impact') or {}).get(
                    'baseMetricV3') or {}).get('cvssV3') or {}).get('baseSeverity')

                cvss_v2 = (((cve_raw.get('impact') or {}).get('baseMetricV2')
                            or {}).get('cvssV2') or {}).get('baseScore')

                cvss_v3 = (((cve_raw.get('impact') or {}).get('baseMetricV3')
                            or {}).get('cvssV3') or {}).get('baseScore')

                software_name = None
                vendor_name = None
                vendor_data = (((cve_raw.get('cve') or {}).get('affects') or {}).get('vendor') or {}).get('vendor_data')
                if vendor_data:
                    # Will only save the first listed software
                    vendor_name = vendor_data[0].get('vendor_name')
                    first_product_data = vendor_data[0].get('product', {}).get('product_data')[0]
                    software_name = first_product_data.get('product_name')

                # Save only what's important
                self.__cve_db[cve_id_from_nvd] = {
                    'id': cve_id_from_nvd,
                    'description': cve_description,
                    'references': cve_references,
                    'severity_v2': cve_severity_v2,
                    'severity_v3': cve_severity_v3,
                    'cvss_v2': cvss_v2,
                    'cvss_v3': cvss_v3,
                    'software_name': software_name,
                    'software_vendor': vendor_name
                }

                # Now parse the list of products affected
                for vendor_raw in cve_raw['cve'].get('affects', {}).get('vendor', {}).get('vendor_data', []):
                    vendor_name = vendor_raw['vendor_name']

                    # This might have '_', we need to filter that out because that's not how we'd get in in the search.
                    vendor_name = vendor_name.replace('_', ' ')

                    if vendor_name not in self.__products_db:
                        self.__products_db[vendor_name] = {}

                    for products_raw in vendor_raw.get('product', {}).get('product_data', []):
                        product_name = products_raw['product_name']
                        product_name = product_name.replace('_', ' ')

                        if product_name not in self.__products_db[vendor_name]:
                            self.__products_db[vendor_name][product_name] = dict()

                        for version_raw in products_raw.get('version', {}).get('version_data', []):
                            version_value = version_raw['version_value']
                            if version_value not in self.__products_db[vendor_name][product_name]:
                                self.__products_db[vendor_name][product_name][version_value] = list()

                            # Each version can be affected by multiple id's. But we might have this cve already
                            # from other artifacts
                            if cve_id_from_nvd not in self.__products_db[vendor_name][product_name][version_value]:
                                self.__products_db[vendor_name][product_name][version_value].append(cve_id_from_nvd)
            except Exception:
                logger.exception(f'Could not parse CVE {cve_raw}, moving on')

        # Try to free memory
        del archive
        del cve_dict
        # pylint: enable=too-many-locals, too-many-nested-blocks

    def search_by_cve(self, cve_id_to_search):
        with self.__use_lock:
            if cve_id_to_search:
                try:
                    return self.__cve_db.get(cve_id_to_search)
                except Exception:
                    logger.exception(f'Could not get CVE data for {cve_id_to_search}')
        return None

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
        if vendor_name == '':
            empty_vendor = True
        else:
            empty_vendor = False
        # pylint: enable=simplifiable-if-statement

        # pylint: disable=too-many-nested-blocks
        with self.__use_lock:
            for db_vendor_name, db_vendor_products in self.__products_db.items():
                # we have to replace all '_' with spaces from now on.
                if str(db_vendor_name).lower() in vendor_name or empty_vendor:
                    for db_vendor_product, db_vendor_product_versions in db_vendor_products.items():
                        if (str(db_vendor_product).lower() in product_name and not empty_vendor) or \
                                (str(db_vendor_product).lower() == product_name and empty_vendor):
                            for db_version, db_version_cves in db_vendor_product_versions.items():
                                if str(db_version).lower() == product_version:
                                    return [self.__cve_db[v] for v in db_version_cves]
        # pylint: enable=too-many-nested-blocks
        return []


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
