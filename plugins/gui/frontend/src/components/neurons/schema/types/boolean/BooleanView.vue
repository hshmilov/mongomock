<template>
  <div class="x-boolean-view">
    <template v-if="typeof processedData !== 'boolean'" />
    <component
      :is="hyperlink? 'a' : 'div'"
      v-else
      :href="hyperlinkHref"
      @click="onClickLink"
    >
      <div
        v-if="processedData"
        class="checkmark"
      />
      <x-cross v-else />
    </component>
  </div>
</template>

<script>
  import xCross from '../../../../axons/visuals/Cross.vue'
  import hyperlinkMixin from '../hyperlink.js'

  export default {
    name: 'XBoolView',
    components: { xCross },
    mixins: [hyperlinkMixin],
    props: ['schema', 'value'],
    computed: {
      processedData () {
        if (Array.isArray(this.value)) {
          if (!this.value.length) return ''
          return this.value.reduce((current, accumulator) => {
            return current || accumulator
          }, true)
        }
        return this.value
      }
    }
  }
</script>

<style lang="scss">
    .x-boolean-view {
        height: 24px;
        display: flex;
        align-items: center;

        .checkmark {
            width: 6px;
            height: 12px;
            transform: rotate(45deg);
            border-bottom: 1px solid;
            border-right: 1px solid;
            margin-left: 4px;
        }
    }
</style>