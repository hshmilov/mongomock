import Vue from 'vue'
import Router from 'vue-router'
import DashboardContainer from '../containers/dashboard/DashboardContainer.vue'
import DevicesContainer from '../containers/device/DevicesContainer.vue'
import DeviceConfigContainer from '../containers/device/DeviceConfigContainer.vue'
import UsersContainer from '../containers/user/UsersContainer.vue'
import ExecutedQueriesContainer from '../containers/device/query/ExecutedQueriesContainer.vue'
import SavedQueriesContainer from '../containers/device/query/SavedQueriesContainer.vue'
import PluginsContainer from '../containers/plugin/PluginsContainer.vue'
import PluginViewContainer from '../containers/plugin/PluginConfigContainer.vue'
import AdaptersContainer from '../containers/adapter/AdaptersContainer.vue'
import AdapterConfigContainer from '../containers/adapter/AdapterConfigContainer.vue'
import ControlContainer from '../containers/control/ControlContainer.vue'
import AlertsContainer from '../containers/alert/AlertsContainer.vue'
import AlertConfigContainer from '../containers/alert/AlertConfigContainer.vue'
import SettingsContainer from '../containers/setting/SettingsContainer.vue'
import NotificationsContainer from '../containers/notification/NotificationContainer.vue'
import NotificationViewContainer from '../containers/notification/NotificationViewContainer.vue'

Vue.use(Router)
export default new Router({
    // This mode prevents '#' appearing in browser url
    mode: 'history',
    routes: [
        {
            path: '/',
            name: 'Dashboard',
			component: DashboardContainer
        },
        {
            path: '/device',
            name: 'Devices',
            component: DevicesContainer,
        },
		{
			path: '/device/:id',
			component: DeviceConfigContainer,
		},
		{
			path: '/device/query/saved',
			name: 'Saved Queries',
			component: SavedQueriesContainer
		},
		{
			path: '/device/query/executed',
			name: 'Queries History',
			component: ExecutedQueriesContainer
		},
		{
			path: '/user',
			name: 'Users',
			component: UsersContainer
		},
		{
            path: '/plugin',
            name: 'Plugins',
            component: PluginsContainer
        },
        {
            path: '/plugin/:id',
            component: PluginViewContainer
        },
        {
            path: '/adapter',
            name: 'Adapters',
            component: AdaptersContainer
        },
		{
			path: '/adapter/:id',
			component: AdapterConfigContainer
		},
        {
            path: '/control',
            name: 'Tasks',
            component: ControlContainer
        },
        {
            path: '/alert',
            name: 'Alerts',
            component: AlertsContainer
        },
		{
			path: '/alert/:id',
			component: AlertConfigContainer
		},
        {
            path: '/settings',
            name: 'Settings',
            component: SettingsContainer
        },
		{
			path: '/notification',
			name: 'Notifications',
			component: NotificationsContainer
		},
		{
			path: '/notification/:id',
			component: NotificationViewContainer
		}
    ]
})