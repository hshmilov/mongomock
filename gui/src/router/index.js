import Vue from 'vue'
import Router from 'vue-router'
import DashboardContainer from '../containers/dashboard/DashboardContainer.vue'
import DevicesContainer from '../containers/device/DevicesContainer.vue'
import QueriesContainer from '../containers/device/query/QueriesContainer.vue'
import PluginsContainer from '../containers/plugin/PluginsContainer.vue'
import PluginViewContainer from '../containers/plugin/PluginViewContainer.vue'
import AdaptersContainer from '../containers/adapter/AdaptersContainer.vue'
import ControlContainer from '../containers/control/ControlContainer.vue'
import AlertsContainer from '../containers/alert/AlertsContainer.vue'
import SettingsContainer from '../containers/setting/SettingsContainer.vue'

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
            path: '/device/query',
            name: 'Queries History',
            component: QueriesContainer
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
            path: '/settings',
            name: 'Settings',
            component: SettingsContainer
        }
    ]
})