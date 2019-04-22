from unifi_adapter.consts import CLIENT_CONFIG_FIELDS, DEFAULT_SITE


def get_client_id(client_config):
    fields = CLIENT_CONFIG_FIELDS
    site = client_config.get(fields.site, DEFAULT_SITE)
    domain = client_config[fields.domain]
    username = client_config[fields.username]
    return '_'.join((username, domain, site))
