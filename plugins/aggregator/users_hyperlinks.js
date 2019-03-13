{
    'associated_devices.device_caption': function (value) {
        return {
            'type': 'query',
            'module': 'devices',
            'filter': 'specific_data.data.hostname == regex("'+value+'", "i") or specific_data.data.name == regex("'+value+'", "i") or specific_data.data.id == regex("'+value+'", "i")'
        }
    }
}