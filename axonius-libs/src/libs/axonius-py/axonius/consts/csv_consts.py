# These are ordered by what we prefer if there are multiple columns (e.g. id > identifier)

IDENTIFIERS = {
    'id': ['id', 'identifier', 'serialnumber', 'assetid', 'resourceid'],
    'name': ['name', 'vmname', 'displayname', 'assetname', 'machinename', 'instancename', 'samaccountname'],
    'hostname': ['host', 'fqdn', 'fullyqualifieddomainname', 'hostname', 'compname', 'computername', 'servername',
                 'dnsname'],
    'mac_address': ['mac', 'macaddress', 'macaddresses', 'macs'],
    'ip': ['ipaddresstext', 'ip', 'ipaddress', 'ipaddresses', 'ips', 'primaryip'],
    'subnetmask': ['ipsubnetmask'],
    'model': ['model', 'modelid'],
    'serial': ['serial', 'serialnumber', 'sn', 'hostserialnumber', 'deviceserialnumber'],
    'os': ['os', 'osname', 'osversion', 'operatingsystem', 'osmode', 'uname'],
    'kernel': ['kernel', 'kernelversion'],
    'manufacturer': ['manufacturer', 'devicemanufacturer'],
    'total_physical_memory_gb': ['memorygb', 'totalmemorygb'],
    'cpu_speed': ['cpuspeedraw'],
    'last_seen': ['lastmessagetime', 'lastdiscoveredtime', 'lastseen'],
    'mail': ['mail', 'email', 'usermail', 'mailaddress', 'emailaddress', 'emailprimarywork'],
    'domain': ['domain', 'domainname'],
    'username': ['username'],
    'first_name': ['firstname', 'givenname'],
    'last_name': ['lastname', 'surname', 'sn'],
    'installed_sw_name': ['softwarename', 'swname'],
    'installed_sw_version': ['softwareversion', 'swversion'],
    'installed_sw_vendor': ['softwarevendor', 'swvendor'],
    'packages': ['packages'],
    'networkinterfaces': ['networkinterfaces']

}

# Note that fields have to be lowercase, with no spaces or - or _. we normalize this when we get data from the csv
# adapter.
for id_name, id_value in IDENTIFIERS.items():
    for value in id_value:
        assert value.lower() == value, f'identifier "{value}" has to be lowercase!'
        assert ' ' not in value, f'no spaces allowed for identifier "{value}"!'
        assert '_' not in value, f'no _ allowed for identifier "{value}"!'
        assert '-' not in value, f'no - allowed for identifier "{value}"!'


def get_csv_field_names(fieldnames):
    """
    iterates over a list of identifiers we defined and tries to see if there are some generic columns in the csv.
    :param fieldnames: list of str with field names
    :return: a dict in which the key is what we search for and the value is the list of column names in the csv
    """

    # transform all fields according to our rules
    fieldnames = {f.lower().replace('_', '').replace('-', '').replace(' ', ''): f for f in fieldnames}

    def search_for_fieldname(list_of_fields_to_search):
        found_fields = []
        for field in list_of_fields_to_search:
            if fieldnames.get(field):
                found_fields.append(fieldnames.get(field))

        return found_fields

    final_dict = dict()
    for key, dict_value in IDENTIFIERS.items():
        column_names = search_for_fieldname(dict_value)
        if column_names:
            final_dict[key] = column_names

    return final_dict
