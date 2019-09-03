
export const entities = [
    {
        name: 'devices', title: 'Devices'
    }, {
        name: 'users', title: 'Users'
    }
]

export const defaultFields = {
    devices: [
        'adapters', 'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.last_seen',
        'specific_data.data.network_interfaces.mac', 'specific_data.data.network_interfaces.ips',
        'specific_data.data.os.type',
        'labels'
    ],
    users: [
        'adapters', 'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
        'specific_data.data.is_admin', 'specific_data.data.last_seen', 'labels'
    ]
}

export const guiPluginName = 'gui'

export const initCustomData = (module) => {
    return {
        action_if_exists: 'update',
        association_type: 'Tag',
        data: {
            id: 'unique'
        },
        entity: module,
        name: guiPluginName,
        plugin_name: guiPluginName,
        plugin_unique_name: guiPluginName,
        type: 'adapterdata',
        id: 'gui_unique'
    }
}