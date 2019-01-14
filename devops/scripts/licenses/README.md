# License Generator
A WIP to output all licenses we have

## how to use
1. Create the final reqs files: `python3 ./generate_licenses.py`
2. on another directory, `mkdir vnev3` and `python3 -m virtualenv --python=python3 venv3` and same for python2
3. `pip3` install -r final_reqs.txt and same for python2
4. for both venv type
```bash
python3 -m piplicenses --with-urls --with-description --order=license --format-confluence
python2 -m piplicenses --with-urls --with-description --order=license --format-confluence
```
5. In the base code, search for `pip3 install`, `pip2 install`, and `pip install` to find additional packages
6. Add 'splunklib' which is part of the splunk adapter, it is the only non pip-installed python library
7. Open any Dockerfile file we have in the code base, collect all apt-get packages and get dependent docker images
8. Open and get_dockerfile methods we have in the code base, collect all apt-get packages and get dependent docker images
9. Raise an empty ubuntu instance, then run init_host.sh and also install all apt-get packages of all Dockerfiles.
Then, use  https://github.com/daald/dpkg-licenses to get the full list of packages
10. Install https://www.npmjs.com/package/license-checker to get licenses for npm
```bash
docker exec -it gui /bin/bash
cd gui
cd frontend
npm install -g license-checker
license-checker --csv --out /path/to/licenses.csv
```