<template>
  <div class="x-boolean-view">
    <template v-for="(item, i) in processedData">
      <component
        :is="hyperlink? 'a' : 'div'"
        :key="i"
        :href="hyperlinkHref"
        :class="{item: true, checkmark: item}"
        @click="onClickLink"
      >
        <x-cross v-if="!item" />
      </component>
    </template>
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
          return this.value
        }
        return [this.value]
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

        .item {
          margin-right: 8px;
        }
    }
</style>