"""
Searches for vulnerable software versions.
"""
import os
import json
import zipfile
import logging
import threading
import requests.exceptions
from general_info.utils.nvd_nist import nvd_update
from axonius.utils.parsing import get_exception_string

logger = logging.getLogger(f"axonius.{__name__}")

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, "artifacts")


class NVDSearcher(object):
    """
    Loads the NVD artifacts into the memory and parses them.
    """

    def __init__(self, download_on_init=True):
        """
        Initializes the class. We have to read all artifacts and load them into the memory.
        """
        self.cve_db = dict()
        self.products_db = dict()
        self.use_lock = threading.Lock()

        if download_on_init is True:
            self.update()   # Update on first usage
        else:
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
            logger.warning(f"Warning, Internet problem. moving on: {get_exception_string()}")
        except Exception:
            logger.exception("Can't update nvd database, loading what's in the disk")
        self._load_artifacts()

    def _load_artifacts(self):
        """
        Loads all artifacts.
        :return:
        """
        with self.use_lock:
            # Delete all we have. It might be incorrect
            self.cve_db = dict()
            self.products_db = dict()

            # Get all files we can update from
            list_dir = os.listdir(ARTIFACT_FOLDER)
            # We want to load artifacts from the oldest to the newest. sort will order this list in the order we want.
            # e.g. ["modified", "2018", "2015", "2017"].sort() == ["2015", "2017", "2018", "modified"]
            list_dir.sort()
            for file_name in list_dir:
                if file_name.endswith(".json.zip"):
                    full_file_name = os.path.join(ARTIFACT_FOLDER, file_name)
                    try:
                        self._parse_artifact(full_file_name)
                    except Exception:
                        logger.exception(f"Failure parsing artifact {full_file_name}. Moving on")

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
                cve_id = cve_raw['cve']['CVE_data_meta']['ID']
                cve_description = None

                # Search for the description. we might have a couple of languages.
                for data in cve_raw['cve'].get('description', {}).get('description_data', []):
                    if data['lang'] == 'en':
                        cve_description = data['value']
                        break

                cve_references = [x.get('url') for x in cve_raw['cve'].get(
                    'references', {}).get('reference_data', []) if x.get('url') is not None]

                cve_severity = cve_raw.get('impact', {}).get(
                    'baseMetricV3', {}).get('cvssV3', {}).get('baseSeverity')

                # Save only what's important
                self.cve_db[cve_id] = {
                    "id": cve_id,
                    "description": cve_description,
                    "references": cve_references,
                    "severity": cve_severity
                }

                # Now parse the list of products affected
                for vendor_raw in cve_raw['cve'].get('affects', {}).get('vendor', {}).get('vendor_data', []):
                    vendor_name = vendor_raw['vendor_name']

                    # This might have '_', we need to filter that out because that's not how we'd get in in the search.
                    vendor_name = vendor_name.replace("_", " ")

                    if vendor_name not in self.products_db:
                        self.products_db[vendor_name] = {}

                    for products_raw in vendor_raw.get('product', {}).get('product_data', []):
                        product_name = products_raw['product_name']
                        product_name = product_name.replace("_", " ")

                        if product_name not in self.products_db[vendor_name]:
                            self.products_db[vendor_name][product_name] = dict()

                        for version_raw in products_raw.get('version', {}).get('version_data', []):
                            version_value = version_raw['version_value']
                            if version_value not in self.products_db[vendor_name][product_name]:
                                self.products_db[vendor_name][product_name][version_value] = list()

                            # Each version can be affected by multiple id's. But we might have this cve already
                            # from other artifacts
                            if cve_id not in self.products_db[vendor_name][product_name][version_value]:
                                self.products_db[vendor_name][product_name][version_value].append(cve_id)
            except Exception:
                logger.exception(f"Couldn't parse CVE {cve_raw}, moving on")

        # Try to free memory
        del archive
        del cve_dict

    def search_vuln(self, vendor_name, product_name, product_version):
        """
        This function checks for the entire cve db to see if we have a match. a match is done, if the vendor name
        in our db is a substring of vendor_name, and, the product name inside our db is a substring of the product name,
        and the version is exactly the version.

        e.g., "Adobe Incorporated Systems", "Adobe Acrobat Reader DC", "15.006.30060" will return a list of all CVE's for this
        product. However we will 'almost' have a few more matches since 'Acrobat Reader' is inside 'Acrobat Reader DC'
        even though its a different product. That is why we require the version to be the same.

        we force the db vendor/product name to be a substring of our input and not vica-versa since usually our input
        is much more detailed. e.g, the vendor of adobe would be "Adobe Incorporated Systems", and the product
        would always include "Adobe" in it (e.g "Adobe Acrobat 2017")

        Do note that we are using the 'affected' field of the nvd dist db, which is not the best solution. The best
        solution would be to parse the 'configuration' because if a cve affects version X "and earlier" we might miss
        that if we are in the earlier. But due to the complicity of searching vulnerabilities and false positives that
        might occur we are not using that (an example of a false positive: Search for "Adobe Acrobat 15.0.0" will
        return a CVE affecting "Adobe Acrobat DC 18.0.0 and earlier". but DC and non-DC are entirely different
        so that's incorrect.
        :param vendor_name:
        :param product_name:
        :param product_version:
        :return:
        """
        with self.use_lock:
            for db_vendor_name, db_vendor_products in self.products_db.items():
                # we have to replace all '_' with spaces from now on.
                if db_vendor_name in vendor_name.lower():
                    for db_vendor_product, db_vendor_product_versions in db_vendor_products.items():
                        if db_vendor_product in product_name.lower():
                            for db_version, db_version_cves in db_vendor_product_versions.items():
                                if db_version == product_version:
                                    return [self.cve_db[v] for v in db_version_cves]

        return []


if __name__ == '__main__':
    db = NVDSearcher()
    cves = db.search_vuln("Adobe Incorporated Systems", "Adobe Acrobat Reader DC", "15.006.30060")

    for cve in cves:
        cve_id = cve['cve']['CVE_data_meta']['ID']
        description = cve['cve']['description']['description_data'][0]['value']
        print(f"CVE {cve_id}:\n{description}\n")
    exit(0)
