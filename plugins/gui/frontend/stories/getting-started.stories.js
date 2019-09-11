import Vue from 'vue'
import { storiesOfAxons } from './index.stories';
import { boolean } from '@storybook/addon-knobs';
import XGettingStarted from '../src/components/networks/getting-started/GettingStarted.vue'
import XMilestone from '../src/components/networks/getting-started/Milestone.vue'

Vue.component('x-milestone', XMilestone);
Vue.component('x-getting-started', XGettingStarted);

storiesOfAxons.add('Getting Started', () => ({
    props: {
      open: {
        default: boolean('open', true)
      }
    },
    template: `<x-getting-started :open="open" />`
  }));