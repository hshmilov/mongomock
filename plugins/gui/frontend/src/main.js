import Vue from 'vue';
import VueWorker from 'vue-worker';
import VueCookies from 'vue-cookies';
import Vuelidate from 'vuelidate';
import VueAnalytics from 'vue-analytics';

import {
  MdSwitch,
  MdDatepicker,
  MdField,
  MdIcon,
  MdButton,
  MdDialog,
  MdCard,
  MdList,
  MdChips,
  MdCheckbox,
  MdMenu,
  MdProgress,
  MdDivider,
  MdDrawer,
} from 'vue-material/dist/components';
import 'vue-svgicon/dist/polyfill';
import * as svgicon from 'vue-svgicon';

import { createVuetifyConfigObject } from './plugins/vuetify';
import App from './components/App.vue';

import SafeguardPlugin from './plugins/safeguard-modal';
import router from './router/index';
import store from './store/index';

Vue.use(Vuelidate);
Vue.use(MdSwitch);
Vue.use(MdDatepicker);
Vue.use(MdField);
Vue.use(MdIcon);
Vue.use(MdButton);
Vue.use(MdDialog);
Vue.use(MdCard);
Vue.use(MdList);
Vue.use(MdChips);
Vue.use(MdCheckbox);
Vue.use(MdMenu);
Vue.use(MdProgress);
Vue.use(MdDivider);
Vue.use(MdDrawer);

Vue.use(VueCookies);
Vue.use(VueWorker);

Vue.use(SafeguardPlugin);

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
