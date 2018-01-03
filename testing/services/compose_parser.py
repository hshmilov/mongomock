import yaml


class ServiceYmlParser(object):
    def __init__(self, compose_file_path):
        self.parsed = yaml.load(open(compose_file_path, "rb").read())

    @property
    def exposed_port(self):
        return int(next(iter(self.parsed['services'].values()))['ports'][0].split(':')[0])

    @property
    def container_name(self):
        return next(iter(self.parsed['services'].values()))['container_name']
