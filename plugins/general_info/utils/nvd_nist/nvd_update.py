"""
Downloads the most recent version of the NVD, then parses it and removes unneeded information.
Requires internet connection to work.
"""
import dateutil.parser
import requests
import os
import sys
import json
from retrying import retry
import logging

logger = logging.getLogger(f"axonius.{__name__}")

# NVD Information is available from 2002. But we don't necessarily want all of it.
NVD_DIST_EARLIEST_YEAR = 2010
NVD_DIST_URL = "https://nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-{version}.{ext}"
MAX_RETRY_FOR_INTERNET_OPERATIONS = 3

# Paths
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_STATE_FILE = os.path.join(CURRENT_DIR, "nvd_current_state.json")
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, "artifacts")


@retry(stop_max_attempt_number=MAX_RETRY_FOR_INTERNET_OPERATIONS)
def get_current_year_online():
    """
    I'm going to assume the clock in this device isn't synchronized, so we'll get the current date.
    This also servers as a check for internet. If we have no internet - this will fail.
    :return: the current year. If we have no internet, this will throw an exception.
    """
    now = requests.get("http://worldclockapi.com/api/json/est/now")
    now.raise_for_status()
    return dateutil.parser.parse(now.json()['currentDateTime']).year


@retry(stop_max_attempt_number=MAX_RETRY_FOR_INTERNET_OPERATIONS)
def get_nvd_sha256_for_version(version):
    """
    Gets the sha256 of the nvd json file for a specific version.
    :param version: the specific version.
    :return: sha256 string.
    """
    res = requests.get(NVD_DIST_URL.format(version=version, ext="meta"))
    res.raise_for_status()

    """
    Example of an output:
    lastModifiedDate:2018-06-25T03:02:21-04:00
    size:28189173
    zipSize:1547680
    gzSize:1547544
    sha256:48148A8A4B48C13F385E7636EB72DAF92AB9C39B50691C2A77F6F076BE3C8064
    """

    data = res.content.decode("ascii")
    for line in data.splitlines():
        if line.startswith("sha256"):
            return line.split(":")[1]

    raise ValueError(f"no sha256 found in data {data}")


@retry(stop_max_attempt_number=MAX_RETRY_FOR_INTERNET_OPERATIONS)
def get_nvd_file_for_version(version):
    """
    Gets the json file for a specific version.
    :param version: the specific version
    :return: a json
    """
    res = requests.get(NVD_DIST_URL.format(version=version, ext="json.zip"))
    res.raise_for_status()

    return res.content


def update(earliest_year=None, hard=False):
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
            with open(CURRENT_STATE_FILE, "rt") as f:
                current_state = json.loads(f.read())
        except Exception:
            pass

    # Get the current year. If we have no internet at any stage we will throw an exception - on purpose.
    current_year = get_current_year_online()

    # Now, we can start downloading the database files. For each year, check if we need to download (with the cache)
    # and then download and parse it. We also download "Modified", which is the file that contains the last 8 days
    # vulnerabilities (it updates each 2 hours)

    list_of_files_to_download = list(range(earliest_year, current_year + 1)) + ["modified"]

    # Note that this is what we also return to the caller if everything succeeds.
    # The caller is expected to parse the files in this specific order, since the "modified" file might contain
    # updated information that should override the information in the other zips.

    for version in list_of_files_to_download:
        sha256 = get_nvd_sha256_for_version(version)
        if current_state.get(str(version)) == sha256:
            # We can continue - we have already taken care of this file.
            print(f"nvdcve-{version} ({sha256}) cached!")
            continue

        current_state[version] = sha256

        # Get the json file
        print(f"Downloading nvdcve-{version}.json.zip..")
        artifact_contents = get_nvd_file_for_version(version)
        with open(os.path.join(ARTIFACT_FOLDER, f"{version}.json.zip"), "wb") as f:
            f.write(artifact_contents)

    # Finally, write the new config
    with open(CURRENT_STATE_FILE, "wt") as f:
        f.write(json.dumps(current_state))

    return list_of_files_to_download


if __name__ == '__main__':
    try:
        _, year = sys.argv
        year = int(year)
    except Exception:
        year = NVD_DIST_EARLIEST_YEAR
    update(year)
    exit(0)
