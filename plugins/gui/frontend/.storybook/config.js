import { configure, addDecorator } from '@storybook/vue';
import Vue from 'vue';
import Vuex from 'vuex';
import { createVuetifyConfigObject } from '../src/plugins/vuetify'

import ProgressGauge from '../src/components/axons/visuals/ProgressGauge.vue';
import {
  MdSwitch, MdField, MdIcon,
  MdDialog, MdCard, MdList, MdChips,
  MdProgress,MdDrawer
} from 'vue-material/dist/components'

Vue.use(Vuex)

Vue.use(MdSwitch)
Vue.use(MdField)
Vue.use(MdIcon)
Vue.use(MdDialog)
Vue.use(MdCard)
Vue.use(MdList)
Vue.use(MdChips)
Vue.use(MdProgress)
Vue.use(MdDrawer)
Vue.component('x-progress-gauge', ProgressGauge);

addDecorator(() => ({
  template: '<v-app><story/></v-app>',
  vuetify: createVuetifyConfigObject()
}));

function loadStories() {
  const req = require.context('../stories', true, /\.stories\.js$/);
  req.keys().forEach(filename => req(filename));
}

configure(loadStories, module);
