export const plugin = {
	state: {
		pluginList: {
			data: [
				{
					unique_plugin_name: 'discovery_plugin',
                    name: 'Discovery', 
                    description: 'Scans the network through connected devices and shows blindspots.', 
                    type: 'Read Only', 
                    isOn: false
                },
				{
					unique_plugin_name: 'correlation_plugin',
                    name: 'Correlation',
                    description: 'Identifies adapters which are connected to the same device and correlates them.', 
                    type: 'Passive',
                    isOn: false
                },
				{
					unique_plugin_name: 'qccpb_plugin',
                    name: 'QCoreCheckPointBlocker', 
                    description: 'Blocks devices from connecting to the network after a certain amount of time they are shutdown.', 
                    type: 'Active', 
                    isOn: true
                }
			]
		},
		fields: [
			{path: 'name', name: 'Name'},
			{path: 'description', name: 'Description'},
			{path: 'type', name: 'Type'}
		],
		pluginDetails: { data: {
			unique_plugin_name: 'qccpb_plugin',
			name: 'QCoreCheckPointBlocker',
			on: true
		}, fetching: false, error: ''}

	},
	getters: {},
	mutations: {},
	actions: {}
}