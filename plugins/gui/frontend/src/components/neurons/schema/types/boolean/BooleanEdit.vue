<template>
  <XSelect
    v-if="enumOptions"
    v-model="data"
    :options="enumOptions"
    @input="input"
  />

  <div
    v-else-if="collapsableSection"
    class="x-section-toggle"
  >
    <ASwitch
      v-model="data"
      :class="{'error-border': error}"
      :disabled="readOnly"
      @focusout.stop="focusout"
      @change="input"
    />
  </div>

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
import { Switch as ASwitch } from 'ant-design-vue';

export default {
  name: 'XBoolEdit',
  components: {
    XSelect, XCheckbox, ASwitch,
  },
  mixins: [primitiveMixin],
  computed: {
    enumOptions() {
      if (_isEmpty(this.schema.enum)) {
        return null;
      }
      return this.schema.enum;
    },
    collapsableSection() {
      return this.schema.name === 'enabled';
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
  .x-section-toggle {
    @include x-switch;
  }
</style>
