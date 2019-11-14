<template functional>
  <div class="x-boolean-view">
    <span
      v-if="props.value === false"
      class="data-false"
    >No</span>
    <span
      v-else-if="props.value === true"
      class="data-true"
    >Yes</span>
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
        required: true
      },
      value: {
        type: Boolean,
        default: null
      }
    }
  }
</script>

<style lang="scss">
    .x-boolean-view {
        height: 24px;
        display: flex;
        align-items: center;
    }
</style>