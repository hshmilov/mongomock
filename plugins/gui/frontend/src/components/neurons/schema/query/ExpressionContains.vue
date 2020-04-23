<template>
  <div class="x-filter-expression-contains">
    <XSelect
      v-model="fieldName"
      :options="options"
      placeholder="Field"
    />
    <input
      v-model="fieldValue"
      placeholder="Segment by..."
    >
    <XButton
      type="link"
      @click="removeFilter"
    >x</XButton>
  </div>
</template>

<script>
import XSelect from '../../../axons/inputs/select/Select.vue';
import XButton from '../../../axons/inputs/Button.vue';

export default {
  name: 'XFilterExpressionContains',
  components: {
    XSelect, XButton,
  },
  props: {
    value: {
      type: Object,
      default: () => ({}),
    },
    options: {
      type: Array,
      default: () => ([]),
    },
  },
  computed: {
    fieldName: {
      get() {
        return this.value.name;
      },
      set(name) {
        this.updateFilter(name, 'name');
      },
    },
    fieldValue: {
      get() {
        return this.value.value;
      },
      set(value) {
        this.updateFilter(value, 'value');
      },
    },
  },
  methods: {
    updateFilter(value, key) {
      const filter = {
        ...this.value,
        [key]: value,
      };
      this.$emit('input', filter);
    },
    removeFilter() {
      this.$emit('remove-filter');
    },
  },
};
</script>

<style lang="scss">
  .x-filter-expression-contains {
    display: grid;
    grid-template-columns: 160px auto 20px;
    grid-gap: 0 8px;
    min-width: 0;
    margin: 8px 0;
  }
</style>
