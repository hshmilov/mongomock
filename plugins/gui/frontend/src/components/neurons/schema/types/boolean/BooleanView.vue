<template functional>
  <div class="x-boolean-view">
    <span
      v-if="props.value === false || props.value === true"
      :class="$options.methods.getClassName(props.value)"
    >{{ $options.methods.format(props.value, props.schema) }}</span>
    <span
      v-else
      class="data-empty"
    >&nbsp;</span>
  </div>
</template>

<script>
export default {
  name: 'XBoolView',
  props: {
    schema: {
      type: Object,
      required: true,
    },
    value: {
      type: Boolean,
      default: null,
    },
  },
  methods: {
    // Populates "User readable" values from the boolean values.
    // If cell renderer given, it will apply it.
    // Otherwise it will set Yes/No according to boolean value.
    format(value, schema) {
      if (schema.cellRenderer) {
        return schema.cellRenderer(value);
      }

      return value ? 'Yes' : 'No';
    },
    // Gets the relevant class name according to the boolean value
    getClassName(value) {
      return value ? 'data-true' : 'data-false';
    },
  },
};
</script>

<style lang="scss">
    .x-boolean-view {
        height: 24px;
        display: flex;
        align-items: center;
    }
</style>
