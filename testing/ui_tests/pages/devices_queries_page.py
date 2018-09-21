from ui_tests.pages.queries_page import QueriesPage


class DevicesQueriesPage(QueriesPage):

    @property
    def url(self):
        return f'{self.base_url}/devices/query/saved'

    @property
    def root_page_css(self):
        return 'li#devices-queries.x-nested-nav-item'

    @property
    def parent_root_page_css(self):
        return 'li#devices.x-nested-nav-item'
