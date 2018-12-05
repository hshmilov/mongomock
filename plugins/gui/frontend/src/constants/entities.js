export const entities = [
    {
        name: 'devices', title: 'Devices'
    }, {
        name: 'users', title: 'Users'
    }
]

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