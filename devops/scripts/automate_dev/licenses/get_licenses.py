#!/usr/bin/env python3

import glob
import json
import re

import csv
import requests
from pip._internal.req import parse_requirements


GO_REPOS = [
    ['facebookincubator/nvdtools', '0.1.4',
     'Apache License 2.0',
     'https://github.com/Axonius/nvdtools/blob/substring_search/LICENSE',
     'We extended the product and vendor name search feature to allow for substring searches in addition to exact matches.']
]


def get_pypi_reqs():
    with open('./pip.csv', 'w') as outputfille:
        lists = glob.glob('./**/requirements*.txt', recursive=True)
        b = []
        for files in lists:
            reqs = parse_requirements(files, session=False)
            packs = [str(pack_list.req) for pack_list in reqs]
            b = b + packs
        splitter = [a.split('==')[0].lower() for a in b]
        for package_name in splitter:
            if package_name == 'pylint':
                continue
            response = requests.get('https://pypi.org/pypi/' + package_name + '/json')
            csv_line = f'{package_name}, {re.sub(",", " ", response.json()["info"]["license"])}, {re.sub(",", " ", response.json()["info"]["summary"])} {", Linking Exception" if package_name == "uwsgi" else ""}\n'
            print(csv_line)
            outputfille.write(csv_line)


def get_npm_reps():
    with open('./npm.csv', 'w') as outputfille:
        with open('./plugins/gui/frontend/package-lock.json') as pack_file:
            data = json.load(pack_file)
            for pack in data['dependencies']:
                new_pack_1 = re.sub('@', '', pack)
                new_pack_2 = re.sub('/', '-', new_pack_1)
                response = requests.get('https://api.npms.io/v2/package/' + new_pack_2)
                try:
                    lic = pack + ',' + data['dependencies'][pack]['version'] + ',' + \
                        response.json()['collected']['metadata']['license'] + ',' + \
                        response.json()['collected']['metadata']['links']['npm'] + '\n'
                    outputfille.write(lic)
                except Exception:
                    continue


def generate_go_csv():
    with open('go.csv', 'w') as csvfile:
        csvwrite = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in GO_REPOS:
            csvwrite.writerow(row)


def main():
    get_npm_reps()
    get_pypi_reqs()
    generate_go_csv()


if __name__ == '__main__':
    main()
