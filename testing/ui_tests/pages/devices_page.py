from ui_tests.pages.entities_page import EntitiesPage


class DevicesPage(EntitiesPage):
    FIELD_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    FIELD_OS_TYPE = 'OS: Type'
    FIELD_ADAPTERS = 'Adapters'
    FIELD_LAST_SEEN = 'Last Seen'

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nested-nav-item'
