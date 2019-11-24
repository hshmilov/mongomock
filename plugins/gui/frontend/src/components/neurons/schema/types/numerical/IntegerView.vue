<template functional>
  <div
    v-if="typeof props.value === 'number'"
    :class="[data.class, data.staticClass]"
    :style="data.staticStyle"
    v-bind="data.attrs"
  >{{ parseInt(props.value) }}</div>
  <div
    v-else
    :class="[data.class, data.staticClass]"
    :style="data.staticStyle"
    v-bind="data.attrs"
  >&nbsp;</div>
</template>
<script>
  export default {
    name: 'XIntegerView',
    props: {
      schema: {
        type: Object,
        required: true
      },
      value: {
        type: Number,
        default: null
      }
    }
  }
</script>

<style lang="scss">

</style>