
import Vue from 'vue';
import VueWorker from 'vue-worker';
import VueCookies from 'vue-cookies';
import Vuelidate from 'vuelidate';
import {
  MdSwitch,
  MdDatepicker,
  MdField,
  MdButton,
  MdDialog,
  MdCard,
  MdList,
  MdChips,
  MdProgress,
  MdDrawer,
  MdContent,
} from 'vue-material/dist/components';

import antInputDirective from 'ant-design-vue/es/_util/antInputDirective';
import { createVuetifyConfigObject } from './plugins/vuetify';
import App from './components/App.vue';

import SafeguardPlugin from './plugins/safeguard-modal';
import RoleGatewayPlugin from './plugins/role-gateway';
import MessageModalPlugin from '@/plugins/message-modal';
import router from './router/index';
import store from './store/index';

Vue.use(antInputDirective);
Vue.use(Vuelidate);
Vue.use(MdSwitch);
Vue.use(MdDatepicker);
Vue.use(MdField);
Vue.use(MdDialog);
Vue.use(MdCard);
Vue.use(MdList);
Vue.use(MdChips);
Vue.use(MdProgress);
Vue.use(MdDrawer);
Vue.use(MdButton);
Vue.use(MdContent);

Vue.use(VueCookies);
Vue.use(VueWorker);

Vue.use(SafeguardPlugin);
Vue.use(MessageModalPlugin);
Vue.use(RoleGatewayPlugin);

new Vue({
  el: '#app',
  vuetify: createVuetifyConfigObject(),
  components: { App },
  template: '<App />',
  router,
  store,
});
