from ui_tests.tests.ui_test_base import TestBase


class TestUsersQuery(TestBase):
    def test_two_property_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.click_query_wizard()
        self.users_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_JSON)
        self.users_page.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS, interval=10)
        assert self.users_page.count_entities() == 1

    def test_subset_query(self):
        # Pick a random query that will have a subset of users that is not the total number and not zero.
        # Below the query bar, above the table and on the left side to the right of the sidebar there should be the word
        # "Users" with parentheses next to it with a number, this should be the number of users displayed in the table.
        # Make sure that the numbers of users displayed in the table matches this number.
        pass

    def test_over_20_query(self):
        # Do a query that results in more then 20 users (Can use testSecDomain credentials to get more users).
        # Click on "50" users per page and validate number of users displayed
        # Click on last page button (far right ">>"), see that it takes you to last page
        pass
