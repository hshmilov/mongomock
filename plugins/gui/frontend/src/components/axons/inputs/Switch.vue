<template>
  <div class="x-switch">
    <ASwitch
      v-bind="$props"
      :disabled="readOnly"
      v-on="$listeners"
    />
    <span class="x-switch-label">{{ label }}</span>
  </div>
</template>

<script>
import { Switch as ASwitch } from 'ant-design-vue';

export default {
  name: 'XSwitch',
  components: { ASwitch },
  props: {
    checked: {
      type: Boolean,
      default: false,
    },
    label: {
      type: String,
      default: '',
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss">
    .ant-switch-checked {
        background-color: #000;
    }
    .x-switch {
      margin-bottom: 0px;

      .x-switch-label {
        margin-left: 10px;
      }
    }
</style>
