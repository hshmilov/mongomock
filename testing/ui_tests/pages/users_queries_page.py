from ui_tests.pages.queries_page import QueriesPage


class UsersQueriesPage(QueriesPage):
    @property
    def url(self):
        return f'{self.base_url}/users/query/saved'

    @property
    def root_page_css(self):
        return 'li#users-queries.x-nav-item'

    @property
    def parent_root_page_css(self):
        return 'li#users.x-nav-item'
