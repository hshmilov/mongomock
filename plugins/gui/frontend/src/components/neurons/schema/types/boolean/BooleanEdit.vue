<template>
  <XSelect
    v-if="enumOptions"
    v-model="data"
    :options="enumOptions"
    @input="input"
  ></XSelect>
  <XCheckbox
    v-else
    :id="schema.name"
    v-model="data"
    :class="{'error-border': error}"
    :read-only="readOnly"
    @focusout.stop="focusout"
    @change="input"
  />
</template>

<script>
import _isEmpty from 'lodash/isEmpty';

import XSelect from '@axons/inputs/select/Select.vue';
import XCheckbox from '@axons/inputs/Checkbox.vue';
import primitiveMixin from '@mixins/primitive';

export default {
  name: 'XBoolEdit',
  components: {
    XSelect, XCheckbox,
  },
  mixins: [primitiveMixin],
  computed: {
    enumOptions() {
      if (_isEmpty(this.schema.enum)) {
        return null;
      }
      return this.schema.enum;
    },
  },
  methods: {
    isEmpty() {
      return this.data === undefined || typeof this.data !== 'boolean';
    },
  },
};
</script>

<style lang="scss">
</style>
