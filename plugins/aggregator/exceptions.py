class AdapterOffline(Exception):
    pass


class ClientsUnavailable(Exception):
    """ Indicate an error fetching clients of adapter, which prevents from querying for devices """
