import Vue from 'vue';
import { storiesOfAxons } from './index.stories';
import { text, boolean } from '@storybook/addon-knobs';
import XButton from '../src/components/axons/inputs/Button.vue';

storiesOfAxons.add('Button', () => ({
  components: { XButton },
  props: {
    disabled: {
      default: boolean('disabled', false)
    },
    inverse: {
      default: boolean('inverse', false)
    },
    inverseEmphasize: {
      default: boolean('inverseEmphasize', false)
    },
    light: {
      default: boolean('light', false)
    },
    right: {
      default: boolean('right', false)
    },
    link: {
      default: boolean('link', false)
    },
    great: {
      default: boolean('great', false)
    },
    emphasize: {
      default: boolean('emphasize', false)
    },
    active: {
      default: boolean('active', false)
    },
    text: {
      default: text('Text', 'Axonius Button')
    }
  },
  template: `<x-button :active="active" :emphasize="emphasize" :link="link" :right="right" :light="light" :inverse="inverse" :inverseEmphasize="inverseEmphasize" :great="great" :disabled="disabled">{{ text }}</x-button>`
}));