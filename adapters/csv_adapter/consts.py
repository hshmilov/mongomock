# These are ordered by what we prefer if there are multiple columns (e.g. id > identifier)

IDENTIFIERS = {
    'id': ['id', 'identifier', 'serialnumber', 'assetid'],
    'name': ['name', 'vmname', 'displayname', 'assetname', 'machinename', 'instancename'],
    'hostname': ['fqdn', 'fullyqualifieddomainname', 'hostname'],
    'mac_address': ['mac', 'macaddress', 'macaddresses', 'macs'],
    'ip': ['ip', 'ipaddress', 'ipaddresses', 'ips'],
    'subnetmask': ['ipsubnetmask'],
    'model': ['model', 'modelid'],
    'serial': ['serial', 'serialnumber', 'sn'],
    'os': ['os', 'osversion', 'operatingsystem', 'osmode'],
    'kernel': ['kernel', 'kernelversion'],
    'manufacturer': ['manufacturer', 'devicemanufacturer'],
    'total_physical_memory_gb': ['memorygb', 'totalmemorygb'],
    'cpu_speed': ['cpuspeedraw'],
    'last_seen': ['lastdiscoveredtime', 'lastseen'],
    'mail': ['mail', 'email', 'usermail', 'mailaddress', 'emailaddress'],
    'domain': ['domain', 'domainname'],
    'username': ['username'],
    'first_name': ['firstname', 'givenname'],
    'last_name': ['lastname', 'surname', 'sn']

}

# Note that fields have to be lowercase, with no spaces or - or _. we normalize this when we get data from the csv
# adapter.
for id_name, id_value in IDENTIFIERS.items():
    for value in id_value:
        assert value.lower() == value, f'identifier "{value}" has to be lowercase!'
        assert ' ' not in value, f'no spaces allowed for identifier "{value}"!'
        assert '_' not in value, f'no _ allowed for identifier "{value}"!'
        assert '-' not in value, f'no - allowed for identifier "{value}"!'
