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
import Report from '../components/pages/Report.vue'
const ExternalViewComponent = () => import('../components/pages/medical/ExternalViewComponent.vue')
const FleetViewer = () => import('../components/pages/medical/FleetViewer.vue')

Vue.use(Router)

let routes

if (ENV.medical) {
    routes = [
        {
            path: '/',
            name: 'Fleet Viewer',
            component: FleetViewer,
        },
        {
            path: '/infuser_programing',
            name: 'Infuser Programing',
            component: ExternalViewComponent,
            props: {medicalUrl: 'pump-programming/pairing', title: 'Infuser Programing'}
        },
        {
            path: '/infuser_manager/drug_list_settings',
            name: 'Drug List Settings',
            component: ExternalViewComponent,
            props: {medicalUrl: 'drugs-list', name: 'Drug List Settings'}
        },
        {
            path: '/infuser_manager/infuser_settings',
            name: 'Infuser Settings',
            component: ExternalViewComponent,
            props: {medicalUrl: 'infuser-settings', name: 'Infuser Settings'}
        },
        {
            path: '/infuser_manager/preset_programs',
            name: 'Preset Programs',
            component: ExternalViewComponent,
            props: {medicalUrl: 'preset-programs', name: 'Preset Programs'}
        },
        {
            path: '/infuser_manager/treatments_settings',
            name: 'Treatments Settings',
            component: ExternalViewComponent,
            props: {medicalUrl: 'programming-tool-settings', name: 'Treatments Settings'}
        },
    ]
} else {
    routes = [
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
            name: 'Device',
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
            component: User,
            name: 'User'
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
            component: Adapter,
            name:'Adapter'
        },
        {
            path: '/enforcements',
            name: 'Enforcements',
            component: Enforcements
        },
        {
            path: '/enforcements/:id',
            component: Enforcement,
            name: 'Enforcement'
        },
        {
            path: '/enforcements/:id/tasks',
            component: Tasks,
            name: 'EnforcementTasks'
        },
        {
            path: '/enforcements/:id/tasks/:taskId',
            component: Task,
            name: 'EnforcementTaskById'
        },
        {
            path: '/tasks',
            name: 'Tasks',
            component: Tasks
        },
        {
            path: '/tasks/:taskId',
            component: Task,
            name: 'Task'
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
            component: Notification,
            name: 'Notification'
        },
        {
            path: '/reports',
            name: 'Reports',
            component: Reports
        },
        {
            path: '/reports/:id',
            component: Report,
            name: 'Report'
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
    ]
}

export default new Router({
    // This mode prevents '#' appearing in browser url
    mode: 'history',
    routes: routes
})