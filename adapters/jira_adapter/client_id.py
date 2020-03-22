def get_client_id(client_config):
    return f'jira://{client_config["domain"]}_{client_config["username"]}_ASSETS'
