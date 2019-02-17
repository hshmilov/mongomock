import Vue from 'vue'
import Router from 'vue-router'
import Account from '../components/pages/Account.vue'
import Adapter from '../components/pages/Adapter.vue'
import Adapters from '../components/pages/Adapters.vue'
import Dashboard from '../components/pages/Dashboard.vue'
import DashboardExplorer from '../components/pages/DashboardExplorer.vue'
import Device from '../components/pages/Device.vue'
import Devices from '../components/pages/Devices.vue'
import DevicesQuery from '../components/pages/DevicesQuery.vue'
import Enforcement from '../components/pages/Enforcement.vue'
import Enforcements from '../components/pages/Enforcements.vue'
import Tasks from '../components/pages/Tasks.vue'
import Task from '../components/pages/Task.vue'
import Instances from '../components/pages/Instances.vue'
import Notification from '../components/pages/Notification.vue'
import Notifications from '../components/pages/Notifications.vue'
import Reports from '../components/pages/Reports.vue'
import Settings from '../components/pages/Settings.vue'
import User from '../components/pages/User.vue'
import Users from '../components/pages/Users.vue'
import UsersQuery from '../components/pages/UsersQuery.vue'
import * as medicalConfig from '../constants/config.json'
import ExternalViewComponent from "../components/pages/medical/ExternalViewComponent.vue";

Vue.use(Router)
export default new Router({
    // This mode prevents '#' appearing in browser url
    mode: 'history',
    routes: !medicalConfig.medical ? [
		{
			path: '/',
			name: 'Dashboard',
			component: Dashboard,
		},
		{
			path: '/dashboard/explorer',
			name: 'Insights Explorer',
			component: DashboardExplorer
		},
        {
            path: '/devices',
            name: 'Devices',
            component: Devices,
        },
		{
			path: '/devices/:id',
			component: Device,
		},
		{
			path: '/devices/query/saved',
			name: 'Device Queries',
			component: DevicesQuery
		},
		{
			path: '/users',
			name: 'Users',
			component: Users
		},
		{
			path: '/users/:id',
			component: User
		},
		{
			path: '/users/query/saved',
			name: 'User Queries',
			component: UsersQuery
		},
        {
            path: '/adapters',
            name: 'Adapters',
            component: Adapters
        },
		{
			path: '/adapters/:id',
			component: Adapter
		},
		{
			path: '/enforcements/tasks',
			name: 'Tasks',
			component: Tasks
		},
		{
			path: '/enforcements/tasks/:id',
			component: Task
		},
        {
            path: '/enforcements',
            name: 'Enforcements',
            component: Enforcements
        },
		{
			path: '/enforcements/:id',
			component: Enforcement
		},
        {
            path: '/settings',
            name: 'Settings',
            component: Settings
        },
		{
			path: '/notifications',
			name: 'Notifications',
			component: Notifications
		},
		{
			path: '/notifications/:id',
			component: Notification
		},
		{
			path: '/reports',
			name: 'Reports',
			component: Reports
		},
		{
			path: '/account',
			name: 'My Account',
			component: Account
		},
        {
            path: '/instances',
            name: 'Instances',
            component: Instances
        }
    ] :
	[
		{
			path: '/',
			name: 'Infuser Manager',
			component: ExternalViewComponent,
			props:	{ medicalUrl: 'pump-programming/pairing', title: 'Infuser Manager' }
		},
		{
			path: '/infuser_settings/drug_list',
			name: 'Drug List',
			component: ExternalViewComponent,
			props: { medicalUrl: 'drugs-list', name: 'Drug List' }
		},
		{
			path: '/infuser_settings/infuser',
			name: 'Infuser',
			component: ExternalViewComponent,
			props: { medicalUrl: 'infuser-settings', name: 'Infuser' }
		},
		{
			path: '/infuser_settings/preset_programs',
			name: 'Preset Programs',
			component: ExternalViewComponent,
			props: { medicalUrl: 'preset-programs', name: 'Preset Programs' }
		},
		{
			path: '/infuser_settings/treatments',
			name: 'Treatments',
			component: ExternalViewComponent,
			props: { medicalUrl: 'programming-tool-settings', name: 'Treatments' }
		},
	]
})