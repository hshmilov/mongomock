<template>
  <div class="x-boolean-view">
    <template v-for="(item, i) in processedData">
      <component
        :is="hyperlink? 'a' : 'div'"
        :key="i"
        :href="hyperlinkHref"
        :class="{item: true}"
        @click="onClickLink"
      >
        <span class="data-false" v-if="item === false">No</span>
        <span class="data-true" v-else-if="item === true">Yes</span>
        <span class="data-empty" v-else></span>
      </component>
    </template>
  </div>
</template>

<script>
    import hyperlinkMixin from '../hyperlink.js'

    export default {
        name: 'XBoolView',
        mixins: [hyperlinkMixin],
        props: ['schema', 'value'],
        computed: {
            processedData() {
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

        .item {
            margin-right: 8px;
        }
    }
</style>