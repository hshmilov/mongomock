import { configure, addDecorator } from '@storybook/vue';
import Vue from 'vue';
import Vuex from 'vuex';
import { createVuetifyConfigObject } from '../src/plugins/vuetify'

import 'vue-svgicon/dist/polyfill';
import * as svgicon from 'vue-svgicon';
import ProgressGauge from '../src/components/axons/visuals/ProgressGauge.vue';
import '../src/components/axons/icons';
import {
  MdSwitch, MdDatepicker, MdField, MdIcon, MdButton, MdDialog, MdCard, MdList, MdChips, MdCheckbox, MdMenu, MdProgress, MdDivider,MdDrawer
} from 'vue-material/dist/components'

Vue.use(Vuex)

Vue.use(MdSwitch)
Vue.use(MdDatepicker)
Vue.use(MdField)
Vue.use(MdIcon)
Vue.use(MdButton)
Vue.use(MdDialog)
Vue.use(MdCard)
Vue.use(MdList)
Vue.use(MdChips)
Vue.use(MdCheckbox)
Vue.use(MdMenu)
Vue.use(MdProgress)
Vue.use(MdDivider)
Vue.use(MdDrawer)
Vue.use(svgicon, { tagName: 'svg-icon' })
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
