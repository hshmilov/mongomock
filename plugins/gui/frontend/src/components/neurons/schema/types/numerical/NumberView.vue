<template functional>
  <div
    v-if="typeof props.value === 'number'"
    :class="[data.class, data.staticClass]"
    :style="data.staticStyle"
    v-bind="data.attrs"
  >{{ props.value.toFixed(2) }}</div>
  <div
    v-else
    :class="[data.class, data.staticClass]"
    :style="data.staticStyle"
    v-bind="data.attrs"
  >&nbsp;</div>
</template>

<script>
    export default {
        name: 'XNumberView',
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