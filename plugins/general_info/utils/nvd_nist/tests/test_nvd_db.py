"""
Tests the NVD db
"""
from .. import nvd_update
from .. import nvd_search
import time


NVD_YEAR_TO_TEST_FROM = 2018


def test_update():
    assert len(nvd_update.update(earliest_year=NVD_YEAR_TO_TEST_FROM, hard=True)) > 1


def test_nvd_search():
    db = nvd_search.NVDSearcher(download_on_init=False)

    def get_cve_with_id(cve_raw_list, cve_id):
        for cve_item in cve_raw_list:
            if cve_item["id"] == cve_id:
                return cve_item

        return None

    start_time = time.time()
    raw = db.search_vuln("Adobe Incorporated Systems", "Adobe Acrobat Reader DC", "15.006.30060")
    assert time.time() - start_time < 5  # max 5 seconds

    cve = get_cve_with_id(raw, "CVE-2018-4916")
    assert cve is not None
    assert cve["id"] == "CVE-2018-4916"
    assert cve["severity"] == "HIGH"
    assert "http://www.securityfocus.com/bid/102994" in cve["references"]
    assert "An issue was discovered in Adobe Acrobat Reader 2018.009.20050 and earlier versions, 2017.011.30070 and " \
           "earlier versions, 2015.006.30394 and earlier versions. The vulnerability is caused by the computation" \
           " that writes data past the end of the intended buffer; the computation is part of the image conversion" \
           " module that handless TIFF data. An attacker can potentially leverage the vulnerability to corrupt" \
           " sensitive data or execute arbitrary code." == cve["description"]
