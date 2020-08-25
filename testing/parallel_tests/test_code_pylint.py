import pytest

import parallel_tests.test_code as _test_code

_NUMBER_OF_PAGES = 12


@pytest.mark.parametrize('page', range(_NUMBER_OF_PAGES))
def test_no_broken_pylint_files(page):
    """Test that every file besides the ones in the exempt list pass pylint"""
    broken_files_list = _test_code.get_unexpected_pylint_state(is_success_expected=True,
                                                               page=page, total_number_of_pages=_NUMBER_OF_PAGES)
    invalid_files = bool(broken_files_list)
    assert not invalid_files, \
        'Broken files found: {}'.format('\n'.join([':'.join(file_desc) for file_desc in broken_files_list]))
