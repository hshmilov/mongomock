from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from ui_tests.pages.entities_page import EntitiesPage


class UsersPage(EntitiesPage):
    FIELD_IMAGE_TITLE = 'Image'
    FIELD_USERNAME_NAME = 'username'
    FIELD_USERNAME_TITLE = 'User Name'
    FIELD_DOMAIN_TITLE = 'Domain'
    FIELD_ADMIN_TITLE = 'Is Admin'
    FIELD_LAST_SEEN_IN_DOMAIN = 'Last Seen In Domain'
    FIELD_LOGON_COUNT = 'Logon Count'

    FILTER_USERNAME = 'specific_data.data.username == regex("{filter_value}")'
    FILTER_IS_ADMIN = '(specific_data.data.is_admin == true)'

    ADMIN_QUERY_NAME = 'Admin Users'

    SYSTEM_DEFAULT_FIELDS = [ADAPTER_CONNECTIONS_FIELD,
                             FIELD_IMAGE_TITLE, FIELD_USERNAME_TITLE, FIELD_DOMAIN_TITLE,
                             FIELD_ADMIN_TITLE, FIELD_LAST_SEEN_IN_DOMAIN,
                             EntitiesPage.FIELD_TAGS]

    @property
    def url(self):
        return f'{self.base_url}/users'

    @property
    def root_page_css(self):
        return 'li#users.x-nav-item'

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Users screen')
        self.click_ok_button()

    def query_user_name_contains(self, string):
        self.run_filter_query(self.FILTER_USERNAME.format(filter_value=string))
