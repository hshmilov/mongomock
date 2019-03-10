import Vue from 'vue'
import Router from 'vue-router'
const Account = () => import('../components/pages/Account.vue')
const Adapter = () => import('../components/pages/Adapter.vue')
const Adapters = () => import('../components/pages/Adapters.vue')
const Dashboard = () => import('../components/pages/Dashboard.vue')
const DashboardExplorer = () => import('../components/pages/DashboardExplorer.vue')
const Device = () => import('../components/pages/Device.vue')
const Devices = () => import('../components/pages/Devices.vue')
const DevicesQuery = () => import('../components/pages/DevicesQuery.vue')
const Enforcement = () => import('../components/pages/Enforcement.vue')
const Enforcements = () => import('../components/pages/Enforcements.vue')
const Tasks = () => import('../components/pages/Tasks.vue')
const Task = () => import('../components/pages/Task.vue')
const Instances = () => import('../components/pages/Instances.vue')
const Notification = () => import('../components/pages/Notification.vue')
const Notifications = () => import('../components/pages/Notifications.vue')
const Reports = () => import('../components/pages/Reports.vue')
const Settings = () => import('../components/pages/Settings.vue')
const User = () => import('../components/pages/User.vue')
const Users = () => import('../components/pages/Users.vue')
const UsersQuery = () => import('../components/pages/UsersQuery.vue')

import * as medicalConfig from '../constants/config.json'
const ExternalViewComponent = () => import("../components/pages/medical/ExternalViewComponent.vue")

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