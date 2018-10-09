import Vue from 'vue'
import Router from 'vue-router'
import DashboardContainer from '../containers/dashboard/DashboardContainer.vue'
import DashboardExplorerContainer from '../containers/dashboard/explorer/DashboardExplorerContainer.vue'
import DevicesContainer from '../containers/device/DevicesContainer.vue'
import DeviceConfigContainer from '../containers/device/DeviceConfigContainer.vue'
import DeviceQueriesContainer from '../containers/device/DeviceQueriesContainer.vue'
import UsersContainer from '../containers/user/UsersContainer.vue'
import UserConfigContainer from '../containers/user/UserConfigContainer.vue'
import UserQueriesContainer from '../containers/user/UserQueriesContainer.vue'
import AdaptersContainer from '../containers/adapter/AdaptersContainer.vue'
import AdapterConfigContainer from '../containers/adapter/AdapterConfigContainer.vue'
import AlertsContainer from '../containers/alert/AlertsContainer.vue'
import AlertConfigContainer from '../containers/alert/AlertConfigContainer.vue'
import SettingsContainer from '../containers/setting/SettingsContainer.vue'
import NotificationsContainer from '../containers/notification/NotificationContainer.vue'
import NotificationViewContainer from '../containers/notification/NotificationViewContainer.vue'
import ReportContainer from '../containers/report/ReportContainer.vue'
import AccountContainer from '../containers/auth/AccountContainer.vue'

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
			path: '/dashboard/explorer',
			name: 'Insights Explorer',
			component: DashboardExplorerContainer
		},
        {
            path: '/devices',
            name: 'Devices',
            component: DevicesContainer,
        },
		{
			path: '/devices/:id',
			component: DeviceConfigContainer,
		},
		{
			path: '/devices/query/saved',
			name: 'Device Queries',
			component: DeviceQueriesContainer
		},
		{
			path: '/users',
			name: 'Users',
			component: UsersContainer
		},
		{
			path: '/users/:id',
			component: UserConfigContainer
		},
		{
			path: '/users/query/saved',
			name: 'User Queries',
			component: UserQueriesContainer
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
		},
		{
			path: '/report',
			name: 'Reports',
			component: ReportContainer
		},
		{
			path: '/account',
			name: 'My Account',
			component: AccountContainer
		}
    ]
})