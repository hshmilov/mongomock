import Vue from 'vue';
import Router from 'vue-router';
import multiguard from 'vue-router-multiguard';
import { LOGOUT } from '@store/modules/auth';
import Administration from '../components/pages/Administration.vue';
import store from '../store/index';

const Account = () => import('../components/pages/Account.vue');
const Adapter = () => import('../components/pages/Adapter.vue');
const Adapters = () => import('../components/pages/Adapters.vue');
const Dashboard = () => import('../components/pages/Dashboard.vue');
const DashboardExplorer = () => import('../components/pages/DashboardExplorer.vue');
const Device = () => import('../components/pages/Device.vue');
const Devices = () => import('../components/pages/Devices.vue');
const Enforcement = () => import('../components/pages/Enforcement.vue');
const Enforcements = () => import('../components/pages/Enforcements.vue');
const Tasks = () => import('../components/pages/Tasks.vue');
const Task = () => import('../components/pages/Task.vue');
const CloudCompliance = () => import('../components/pages/CloudCompliance.vue');
const Instances = () => import('../components/pages/Instances.vue');
const Notification = () => import('../components/pages/Notification.vue');
const Notifications = () => import('../components/pages/Notifications.vue');
const Reports = () => import('../components/pages/Reports.vue');
const Settings = () => import('../components/pages/Settings.vue');
const User = () => import('../components/pages/User.vue');
const Users = () => import('../components/pages/Users.vue');
const Report = () => import('../components/pages/Report.vue');

const xDevicesSavedQueries = () => import('../components/pages/DevicesSavedQueries');
const xUsersSavedQueries = () => import('../components/pages/UsersSavedQueries');

Vue.use(Router);

const adminGuard = (to, from, next) => {
  let unWatch = null;
  const proceed = () => {
    if (unWatch) {
      unWatch();
    }
    if (store.state.auth.currentUser.data.admin
      || store.state.auth.currentUser.data.role_name === 'Admin') {
      next();
    } else {
      store.dispatch(LOGOUT)
        .then(() => next('/'))
        .catch(() => next('/'));
    }
  };
  // currently there is no way to know if the store load the current user data
  // and got all the info
  // we set a watch on the user_name property and wait for the value
  if (!store.state.auth.currentUser.data.user_name) {
    unWatch = store.watch(
      (state) => state.auth.currentUser.data.user_name,
      (userName) => {
        if (userName) {
          proceed();
        }
      },
    );
  } else {
    proceed();
  }
};

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/dashboard/explorer',
    name: 'Insights Explorer',
    component: DashboardExplorer,
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
    path: '/devices/query/saved/:queryId?',
    name: 'devices-queries',
    component: xDevicesSavedQueries,
  },
  {
    path: '/users',
    name: 'Users',
    component: Users,
  },
  {
    path: '/users/:id',
    component: User,
    name: 'User',
  },
  {
    path: '/users/query/saved/:queryId?',
    name: 'users-queries',
    component: xUsersSavedQueries,
  },
  {
    path: '/adapters',
    name: 'Adapters',
    component: Adapters,
  },
  {
    path: '/adapters/:id',
    component: Adapter,
    name: 'Adapter',
  },
  {
    path: '/enforcements',
    name: 'Enforcements',
    component: Enforcements,
  },
  {
    path: '/enforcements/:id',
    component: Enforcement,
    name: 'Enforcement',
  },
  {
    path: '/enforcements/:id/tasks',
    component: Tasks,
    name: 'EnforcementTasks',
  },
  {
    path: '/enforcements/:id/tasks/:taskId',
    component: Task,
    name: 'EnforcementTaskById',
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: Tasks,
  },
  {
    path: '/tasks/:taskId',
    component: Task,
    name: 'Task',
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: Notifications,
  },
  {
    path: '/notifications/:id',
    component: Notification,
    name: 'Notification',
  },
  {
    path: '/reports',
    name: 'Reports',
    component: Reports,
  },
  {
    path: '/reports/:id',
    component: Report,
    name: 'Report',
  },
  {
    path: '/account',
    name: 'My Account',
    component: Account,
  },
  {
    path: '/instances',
    name: 'Instances',
    component: Instances,
  },
  {
    path: '/cloud_asset_compliance/:id?',
    component: CloudCompliance,
    name: 'Cloud Asset Compliance',
  },
  {
    path: '/administration',
    component: Administration,
    name: 'Administration',
    beforeEnter: multiguard([adminGuard]),
  },
];

export default new Router({
  // This mode prevents '#' appearing in browser url
  mode: 'history',
  routes,
});
