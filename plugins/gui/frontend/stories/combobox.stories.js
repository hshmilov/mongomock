import Vue from 'vue';
import { storiesOfAxons } from './index.stories';
import { boolean, number, array } from '@storybook/addon-knobs';
import xCombobox from '../src/components/axons/inputs/combobox/index.vue';

Vue.component('x-combobox', xCombobox)

storiesOfAxons.add('Combobox', () => ({
  props: {
    value: {
      default: array('value', [
        'g - selected', 'a - selected'
      ])
    },
    items: {
      default: array('items', [
        'a - selected', 'b - indeterminate', 'e', 'c - indeterminate', 'g - selected', 'd', 'f'
      ])
    },
    indeterminate: {
      default: array('indeterminate', [
        'b - indeterminate', 'c - indeterminate'
      ])
    },
    selectionDisplayLimit: {
      default: number('selectionDisplayLimit', 3)
    },
    multiple: {
      default: boolean('multiple', true)
    },
    keepOpen: {
      default: boolean('keepOpen', true)
    }
  },
  template: `
        <v-container fluid>
            <v-row>
                <v-col cols="6">
                    <x-combobox
                    :value="value"
                    :items="items"
                    :indeterminate="indeterminate"
                    :selection-display-limit="selectionDisplayLimit"
                    :multiple="multiple"
                    :keep-open="keepOpen"
                    />
                </v-col>
            </v-row>
        </v-container>
             `
}));