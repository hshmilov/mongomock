from ui_tests.pages.entities_page import EntitiesPage


class UsersPage(EntitiesPage):
    FIELD_USERNAME_NAME = 'username'

    @property
    def url(self):
        return f'{self.base_url}/users'

    @property
    def root_page_css(self):
        return 'li#users.x-nested-nav-item'

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Users screen')
        self.click_ok_button()
