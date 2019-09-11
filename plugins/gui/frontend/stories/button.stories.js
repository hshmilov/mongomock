import Vue from 'vue';
import { storiesOfAxons } from './index.stories';
import { withKnobs, text, boolean } from '@storybook/addon-knobs';

storiesOfAxons.add('XButton', () => ({
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
  template: `<x-button :active="active" :emphasize="emphasize" :link="link" :right="right" :light="light" :invers="invers" :inverseEmphasize="inverseEmphasize" :great="great" :disabled="disabled">{{ text }}</x-button>`
}));