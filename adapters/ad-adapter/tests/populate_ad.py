import ldap3
import json
import uuid
import codenamize


data_schema = {
    #"dNSHostName" : "{computer_name}.TestSecDomain.test",
    #"lastLogoff" : "Mon, 01 Jan 1601 00:00:00 GMT",
    #"lastLogon" : "Mon, 25 Dec 2017 10:18:33 GMT",
    #"lastLogonTimestamp" : "Thu, 21 Dec 2017 12:46:32 GMT",
    "objectClass": [
        "top",
        "person",
        "organizationalPerson",
        "user",
        "computer"
    ],
    "operatingSystem": "Windows 10 Pro",
    "operatingSystemVersion": "10.0 (15063)",
    "userAccountControl": 4096
    #"primaryGroupID" : 515,
    #"pwdLastSet" : "Thu, 07 Dec 2017 09:08:22 GMT",
    #"sAMAccountName" : "{computer_name}$",
    #"sAMAccountType" : 805306369,
    #"servicePrincipalName" : [
    #    "RestrictedKrbHost/{computer_name}",
    #    "HOST/{computer_name}",
    #    "RestrictedKrbHost/{computer_name}.TestSecDomain.test",
    #    "HOST/{computer_name}.TestSecDomain.test"
    #],
    #"uSNChanged" : 22181,
    #"uSNCreated" : 12816,
    #"userAccountControl" : 4096,
    #"whenChanged" : "Thu, 21 Dec 2017 12:46:32 GMT",
    #"whenCreated" : "Mon, 06 Nov 2017 14:15:18 GMT"
}

data_schema_text = json.dumps(data_schema)

server_address = "10.0.229.9"
username = "TestSecDomain\\Administrator"
password = "&P?HBx-e3s"
domain_to_add = "DC=TestSecDomain,DC=test"
OU = "OU=TestOrg"
address = OU + ',' + domain_to_add
devices_num = 100000

schema = "CN={computer_name} ,{address}"

ldap_server = ldap3.Server(server_address, connect_timeout=10)
ldap_connection = ldap3.Connection(ldap_server, user=username, password=password,
                                   raise_exceptions=True, receive_timeout=10)
ldap_connection.bind()

# temp_text = data_schema_text[1:-1].format(computer_name="ofir",
#                                                address=address,
#                                                domain_to_add=domain_to_add,
#                                                uuid=str(uuid.uuid1()))
#current_data_schema = json.loads("{" + temp_text + "}")

for i in range(0, devices_num):
    if i % 100 == 0:
        print(i)
    current_name = codenamize.codenamize(i) + "-PC"
    try:
        ldap_connection.add(schema.format(computer_name=current_name,
                                          address=address),
                            attributes=data_schema)
    except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
        print("Entry already exist")
        pass
