"""
Downloads the most recent version of the NVD, then parses it and removes unneeded information.
Requires internet connection to work.
"""
import itertools
import json
import logging
import os
import sys
import pickle
from urllib.parse import urlparse

import requests
from retrying import retry

from axonius.clients.rest.connection import RESTConnection
from axonius.consts.system_consts import CORTEX_PATH

logger = logging.getLogger(f'axonius.{__name__}')

# NVD Information is available from 2002. But we don't necessarily want all of it.
NVD_DIST_EARLIEST_YEAR = 2002
NVD_DIST_URL = 'https://nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-{version}.{ext}'
MAX_RETRY_FOR_INTERNET_OPERATIONS = 3
TIMEOUT_FOR_REQUESTS_IN_SECONDS = 15

# Paths
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_STATE_FILE = os.path.join(CURRENT_DIR, 'nvd_current_state.json')
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, 'artifacts')

NVD_ARTIFACTS_URL = 'https://davinci.axonius.lan:1001/'
NVD_ARTIFACTS_PATH = os.path.join(CORTEX_PATH, 'plugins', 'static_analysis', 'nvd_nist', 'artifacts')

# pylint: disable=invalid-triple-quote, pointless-string-statement


@retry(stop_max_attempt_number=MAX_RETRY_FOR_INTERNET_OPERATIONS)
def get_nvd_sha256_for_version(version):
    """
    Gets the sha256 of the nvd json file for a specific version.
    :param version: the specific version.
    :return: sha256 string.
    """
    res = requests.get(NVD_DIST_URL.format(version=version, ext='meta'), timeout=TIMEOUT_FOR_REQUESTS_IN_SECONDS)
    res.raise_for_status()

    """
    Example of an output:
    lastModifiedDate:2018-06-25T03:02:21-04:00
    size:28189173
    zipSize:1547680
    gzSize:1547544
    sha256:48148A8A4B48C13F385E7636EB72DAF92AB9C39B50691C2A77F6F076BE3C8064
    """

    data = res.content.decode('ascii')
    for line in data.splitlines():
        if line.startswith('sha256'):
            return line.split(':')[1]

    raise ValueError(f'no sha256 found in data {data}')
# pylint: enable=invalid-triple-quote, pointless-string-statement


@retry(stop_max_attempt_number=MAX_RETRY_FOR_INTERNET_OPERATIONS)
def get_nvd_file_for_version(version):
    """
    Gets the json file for a specific version.
    :param version: the specific version
    :return: a json
    """
    res = requests.get(NVD_DIST_URL.format(version=version, ext='json.zip'), timeout=TIMEOUT_FOR_REQUESTS_IN_SECONDS)
    res.raise_for_status()

    return res.content


def update_from_internal_cache():
    """
    Simply calls the download artifacts script to download things from the internet before we create the installer.
    :return:
    """
    # Download nvd artifacts
    print(f'Downloading NVD artifacts from {NVD_ARTIFACTS_URL}...')
    response = requests.get(NVD_ARTIFACTS_URL, verify=False, timeout=60)
    response.raise_for_status()
    for file_name in response.json():
        print(f'Downloading {NVD_ARTIFACTS_URL + file_name}...')
        response = requests.get(NVD_ARTIFACTS_URL + file_name, verify=False, timeout=60)
        response.raise_for_status()
        with open(os.path.join(NVD_ARTIFACTS_PATH, file_name.split('/')[-1]), 'wb') as f:
            f.write(response.content)

    print(f'Done downloading NVD Artifacts')


def update(earliest_year=None, hard=False, from_internal_cache=True):
    if from_internal_cache:
        parsed_url = urlparse(NVD_ARTIFACTS_URL)
        if RESTConnection.test_reachability(parsed_url.hostname, parsed_url.port):
            update_from_internal_cache()
    else:
        update_from_internet(earliest_year, hard)


def update_from_internet(earliest_year=None, hard=False):
    """
    Downloads the files from the internet.
    :param earliest_year: the earliest nvd db year to download.
    :param hard: if True, downloads everything from scratch. Else, caches (checks for sha256)
    :return:
    """
    if earliest_year is None:
        earliest_year = NVD_DIST_EARLIEST_YEAR

    assert earliest_year >= 2002

    current_state = {}
    if hard is False:
        # Get current-state file. This is a json that has the sha256 of the files we have parsed.
        # We use this to cache our downloads.
        try:
            with open(CURRENT_STATE_FILE, 'rt') as f:
                current_state = json.loads(f.read())
        except Exception:
            pass

    # Now, we can start downloading the database files. For each year, check if we need to download (with the cache)
    # and then download and parse it. We also download 'Modified', which is the file that contains the last 8 days
    # vulnerabilities (it updates each 2 hours)
    files_iterator = itertools.chain(itertools.count(earliest_year), ['modified'])

    # Note that this is what we also return to the caller if everything succeeds.
    # The caller is expected to parse the files in this specific order, since the 'modified' file might contain
    # updated information that should override the information in the other zips.

    memory_usage = 0
    for version in files_iterator:
        try:
            sha256 = get_nvd_sha256_for_version(version)
        except requests.exceptions.HTTPError as err:
            logger.info(f'Failed to fetch year {version}, giving up')
            break
        if current_state.get(str(version)) == sha256:
            # We can continue - we have already taken care of this file.
            print(f'nvdcve-{version} ({sha256}) cached!')
            continue

        current_state[version] = sha256

        # Get the json file
        print(f'Downloading nvdcve-{version}.json.zip..')
        try:
            artifact_contents = get_nvd_file_for_version(version)
        except requests.exceptions.HTTPError as err:
            logger.info(f'Failed to fetch year {version}, giving up')
            break
        # Get the size of the downloaded file in MB
        file_size = sys.getsizeof(pickle.dumps(artifact_contents)) / 1024 / 1024
        memory_usage += file_size
        print(f'Size of nvdcve-{version}.json.zip is {round(file_size, 2)} MB')
        with open(os.path.join(ARTIFACT_FOLDER, f'{version}.json.zip'), 'wb') as f:
            f.write(artifact_contents)

    # Finally, write the new config
    with open(CURRENT_STATE_FILE, 'wt') as f:
        f.write(json.dumps(current_state))
    print(f'Total memory usage is {round(memory_usage, 2)} MB')


def main(year=NVD_DIST_EARLIEST_YEAR):
    year = int(year)
    update(year)
    return 0


if __name__ == '__main__':
    exit(main(*sys.argv[1:]))
