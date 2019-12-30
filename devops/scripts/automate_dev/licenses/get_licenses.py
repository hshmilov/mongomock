#!/usr/bin/env python3

from pip._internal.req import parse_requirements
import glob
import requests
import json
import re
import docker
from io import BytesIO


def get_pypi_reqs():
    with open("./pip.csv", "w") as outputfille:
        lists = glob.glob('./**/requirements*.txt', recursive=True)
        b = []
        for files in lists:
            reqs = parse_requirements(files, session=False)
            packs = [str(pack_list.req) for pack_list in reqs]
            b = b + packs
        splitter = [a.split('==') for a in b]
        for set_lower in splitter:
            set_lower[0] = set_lower[0].lower()
            response = requests.get('https://pypi.org/pypi/' + str(set_lower[0]) + '/json')
            outputfille.write(set_lower[0] + "," + re.sub(',', ' ', response.json()['info']
                                                          ['license']) + "," + re.sub(',', ' ', response.json()['info']['summary'] + "\n"))
    outputfille.close()


def get_npm_reps():
    with open("./npm.csv", "w") as outputfille:
        with open("./plugins/gui/frontend/package-lock.json") as pack_file:
            data = json.load(pack_file)
            for pack in data['dependencies']:
                new_pack_1 = re.sub('@', '', pack)
                new_pack_2 = re.sub('/', '-', new_pack_1)
                response = requests.get('https://api.npms.io/v2/package/' + new_pack_2)
                try:
                    lic = pack + "," + data['dependencies'][pack]['version'] + "," + response.json(
                    )['collected']['metadata']['license'] + "," + response.json()['collected']['metadata']['links']['npm'] + "\n"
                    outputfille.write(lic)
                except Exception:
                    continue
    outputfille.close()


def get_dock():
    with open("./apt.csv", "w") as outputfille:
        client = docker.from_env()
        dockerfile = '''
            FROM nexus.axonius.lan/axonius/axonius-base-image
            ADD ./devops/scripts/automate_dev/licenses/dpkg-licenses ./dpkg-licenses
            RUN chmod +x ./dpkg-licenses/dpkg-licenses
            CMD ./dpkg-licenses/dpkg-licenses
        '''
        f = BytesIO(dockerfile.encode('utf-8'))
        for line in client.api.build(fileobj=f, rm=True, tag='get_license:1.0'):
            continue
        apt_list = client.containers.run(image='get_license:1.0').decode()
        client.images.remove('get_license:1.0', force=True)
        outputfille.write(apt_list)
    outputfille.close()


def main():
    get_npm_reps()
    get_pypi_reqs()
    get_dock()


if __name__ == '__main__':
    main()
