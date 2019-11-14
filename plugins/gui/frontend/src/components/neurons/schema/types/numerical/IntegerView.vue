<template functional>
  <div v-if="typeof props.value === 'number'">{{ parseInt(props.value) }}</div>
  <div v-else>&nbsp;</div>
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