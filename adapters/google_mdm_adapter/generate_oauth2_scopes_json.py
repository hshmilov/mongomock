"""
Parses HTML and generates a json of oauth2 scopes
"""
import json
import re
from collections import defaultdict

import requests


def main():
    scopes_html_response = requests.get('https://developers.google.com/identity/protocols/googlescopes')
    scopes_html_response.raise_for_status()
    content = scopes_html_response.text

    all_scopes = defaultdict(set)

    for url, description in re.findall('<tr><td>(.*)</td><td>(.*)</td></tr>', content):
        all_scopes[url].add(description)

    all_scopes = {scope: ','.join(list(description)) for scope, description in all_scopes.items()}
    with open('oauth2_scopes.json', 'wt') as f:
        f.write(json.dumps(all_scopes, indent=6))

    return 0


if __name__ == '__main__':
    exit(main())
