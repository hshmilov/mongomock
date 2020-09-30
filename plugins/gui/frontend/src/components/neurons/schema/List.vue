<template>
  <div class="x-list">
    <div class="list-actions">
      <XButton
        type="link"
        @click="expandAll"
      >+ Expand All</XButton>
      <XButton
        type="link"
        @click="collapseAll"
      >- Collapse All</XButton>
    </div>
    <XArrayView
      ref="arrayView"
      :value="data"
      :schema="schema"
    />
  </div>
</template>

<script>
import XArrayView from './types/array/ArrayView.vue';

/*
      Dynamically built list of nested data, structured according to given schema, filled with given value.
      Schema is expected to be of type array (can be tuple). Data is expected to comply to given schema's definition.
      If limit is on, only data included in 'required' will be presented.
   */
export default {
  name: 'XList',
  components: { XArrayView },
  props: {
    data: {
      required: true,
    },
    schema: {
      required: true,
    },
  },
  methods: {
    expandAll() {
      this.$refs.arrayView.collapseRecurse(false);
    },
    collapseAll() {
      this.$refs.arrayView.collapseRecurse(true);
    },
  },
};
</script>

<style lang="scss">
    .x-list {
        .list-actions {
            display: flex;
            justify-content: flex-end;
            overflow: hidden;

            .x-button {
                font-size: 12px;
            }
        }
    }
</style>
