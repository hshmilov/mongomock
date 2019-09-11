import { configure } from '@storybook/vue';
import Vue from 'vue';
import 'vue-svgicon/dist/polyfill'
import * as svgicon from 'vue-svgicon'
import XButton from '../src/components/axons/inputs/Button';
import ProgressGauge from '../src/components/axons/visuals/ProgressGauge'
import '../src/components/axons/icons'
import {
  MdSwitch, MdDatepicker, MdField, MdIcon, MdButton, MdDialog, MdCard, MdList, MdChips, MdCheckbox, MdMenu, MdProgress, MdDivider,MdDrawer
} from 'vue-material/dist/components'
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
Vue.use(MdDivider),
Vue.use(MdDrawer),
Vue.use(svgicon, { tagName: 'svg-icon' })
Vue.component('x-button', XButton);
Vue.component('x-progress-gauge', ProgressGauge);

function loadStories() {
  const req = require.context('../stories', true, /\.stories\.js$/);
  req.keys().forEach(filename => req(filename));
}

configure(loadStories, module);
