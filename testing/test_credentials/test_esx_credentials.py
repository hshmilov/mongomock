
client_details = [
    ({
        "host": "vcenter.axonius.lan",
        "user": "administrator@vsphere.local",
        "password": "Br!ng0rder",
        "verify_ssl": False
    }, '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'),
    # This vcenter is currently not active!!! we should return it as soon as it becomes active again
    # ({
    #     "host": "vcenter51.axonius.lan",
    #     "user": "root",
    #     "password": "vmware",
    #     "verify_ssl": False
    # }, "525345eb-51ef-f4d7-85bb-08e521b94528"),
    ({
        "host": "vcenter55.axonius.lan",
        "user": "root",
        "password": "vmware",
        "verify_ssl": False
    }, "525d738d-c18f-ed57-6059-6d3378a61442")]

# vcenter vm
SOME_DEVICE_ID = '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'
# this is the ID of a VM that is inside a datacenter that is inside a folder
# it is called "just_for_datacenter_folders"
AGGREGATED_DEVICE_ID = "5011b327-7833-4d80-af9f-11c0afdde448"
