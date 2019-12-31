import Vue from 'vue';
import { storiesOfAxons } from './index.stories';
import { boolean, number, array } from '@storybook/addon-knobs';
import xSelectBox from '../src/components/axons/inputs/select/SelectBox.vue';

Vue.component('x-select-box', xSelectBox)

storiesOfAxons.add('Select Box', () => ({
  props: {
    value: {
      default: array('value', [
        'Item 6', 'Item 2'
      ])
    },
    items: {
      default: array('items', [
        'Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5', 'Item 6', 'Item 7'
      ])
    },
    indeterminate: {
      default: array('indeterminate', [
        'Item 3', 'Item 5'
      ])
    },
    selectionDisplayLimit: {
      default: number('selectionDisplayLimit', 3)
    },
    multiple: {
      default: boolean('multiple', false)
    },
    keepOpen: {
      default: boolean('keepOpen', false)
    }
  },
  template: `<x-select-box
               :value="value"
               :items="items"
               :indeterminate="indeterminate"
               :selection-display-limit="selectionDisplayLimit"
               :multiple="multiple"
               :keep-open="keepOpen"
             />`
}));