
client_details = {
    # see https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal
    # for how to create client id + secret for axonius application.
    # set role as Reader
    'client_id': '1a287e13-c83b-47c8-878c-6a9ec028cac2',
    'client_secret': 'NM757L01BJ81XSqWfxqCKnKlCtFeAgJ1/YwGotHp9D8=',

    # tenant_id is the Directory ID of the Azure Active Directory (see previous link)
    'tenant_id': 'a02ef90b-a415-4ff5-98ba-23d3600e084b',

    # see https://blogs.msdn.microsoft.com/mschray/2016/03/18/getting-your-azure-subscription-guid-new-portal/
    # subscription_id is the id of the subscription (in our case, currently it is the "Axonius-Azure"
    'subscription_id': 'ba4aa321-c802-4de2-bb72-ca4c66b5b124',
}

SOME_DEVICE_ID = '/subscriptions/ba4aa321-c802-4de2-bb72-ca4c66b5b124/resourceGroups/MYRESOURCEGROUP/providers/Microsoft.Compute/virtualMachines/win-test-server'  # win-test-server
