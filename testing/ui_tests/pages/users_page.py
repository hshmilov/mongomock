from ui_tests.pages.entities_page import EntitiesPage


class UsersPage(EntitiesPage):

    @property
    def url(self):
        return f'{self.base_url}/users'

    @property
    def root_page_css(self):
        return 'li#users.x-nested-nav-item'
