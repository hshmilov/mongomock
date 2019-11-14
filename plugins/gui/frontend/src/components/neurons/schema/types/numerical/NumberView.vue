<template functional>
  <div v-if="typeof props.value === 'number'">{{ props.value.toFixed(2) }}</div>
  <div v-else>&nbsp;</div>
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