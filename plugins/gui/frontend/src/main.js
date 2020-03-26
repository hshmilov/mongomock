
import Vue from 'vue';
import VueWorker from 'vue-worker';
import VueCookies from 'vue-cookies';
import Vuelidate from 'vuelidate';
import VueAnalytics from 'vue-analytics';

import { Modal, Button, Menu, Dropdown, Checkbox, Select, Icon } from 'ant-design-vue';

Vue.use(Modal);
Vue.use(Button);
Vue.use(Menu);
Vue.use(Dropdown);
Vue.use(Checkbox);
Vue.use(Select);
Vue.use(Icon);


import {
  MdSwitch,
  MdDatepicker,
  MdField,
  MdButton,
  MdIcon,
  MdDialog,
  MdCard,
  MdList,
  MdChips,
  MdProgress,
  MdDrawer,
} from 'vue-material/dist/components';
import 'vue-svgicon/dist/polyfill';
import * as svgicon from 'vue-svgicon';

import { createVuetifyConfigObject } from './plugins/vuetify';
import App from './components/App.vue';

import SafeguardPlugin from './plugins/safeguard-modal';
import RoleGatewayPlugin from './plugins/role-gateway';
import router from './router/index';
import store from './store/index';

Vue.use(Vuelidate);
Vue.use(MdSwitch);
Vue.use(MdDatepicker);
Vue.use(MdField);
Vue.use(MdIcon);
Vue.use(MdDialog);
Vue.use(MdCard);
Vue.use(MdList);
Vue.use(MdChips);
Vue.use(MdProgress);
Vue.use(MdDrawer);
Vue.use(MdButton);

Vue.use(VueCookies);
Vue.use(VueWorker);

Vue.use(SafeguardPlugin);
Vue.use(RoleGatewayPlugin);

Vue.use(svgicon, { tagName: 'SvgIcon' });

Vue.use(VueAnalytics, {
  id: 'UA-123123123-0', // set in backend
  router,
  customResourceURL: '/src/analytics.js',
});

new Vue({
  el: '#app',
  vuetify: createVuetifyConfigObject(),
  components: { App },
  template: '<App />',
  router,
  store,
});
