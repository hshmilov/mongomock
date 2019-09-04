import { configure } from '@storybook/vue';
import Vue from 'vue';
import XButton from '../src/components/axons/inputs/Button';
import ProgressGauge from '../src/components/axons/visuals/ProgressGauge'

Vue.component('x-button', XButton);
Vue.component('x-progress-gauge', ProgressGauge);

function loadStories() {
  const req = require.context('../stories', true, /\.stories\.js$/);
  req.keys().forEach(filename => req(filename));
}

configure(loadStories, module);