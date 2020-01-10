<template>
  <div class="x-array-raw-view">
    <div
      v-for="item in valuableItems"
      :key="item.name"
      class="item"
    >
      <label class="item__label">{{ item.title }}:</label>
      <div class="item__value">{{ value[item.name] }}</div>
    </div>
  </div>
</template>

<script>
  import _get from 'lodash/get'
  import _isEmpty from 'lodash/isEmpty'

  export default {
    name: 'XArrayRawView',
    props: {
      value: {
        type: Object,
        required: true
      },
      schema: {
          type: Object,
        required: true
      }
    },
    computed: {
      valuableItems () {
        return this.schema.items.filter(item => !_isEmpty(_get(this.value, item.name)))
      }
    }
  }
</script>

<style lang="scss">
  .x-array-raw-view {
    display: grid;
    grid-gap: 0 4px;
    grid-auto-flow: column;
    line-height: 24px;
    height: 24px;

    .item {
      display: flex;

      &__label {
        font-weight: 300;
      }

      &__value {
        margin-left: 4px;
      }
    }
  }
</style>