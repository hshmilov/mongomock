<template>
  <md-chip class="x-array-raw-view">
    <div
      v-for="item in valuableItems"
      :key="item.name"
      class="item"
    >
      <label>{{ item.title }}:</label>
      <div class="value">{{ data[item.name] }}</div>
    </div>
  </md-chip>
</template>

<script>
  export default {
    name: 'XArrayRawView',
    props: {
        data: {
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
        return this.schema.items.filter(item =>
          this.data[item.name] !== undefined && this.data[item.name] !== null && this.data[item.name] !== '')
      }
    }
  }
</script>

<style lang="scss">
    .x-array-raw-view {
        display: grid;
        grid-gap: 0 4px;
        grid-auto-flow: column;
        align-items: center;
        background-color: rgba($grey-3, 0.2);
        height: 24px;
        line-height: 24px;
        .item {
            label {
                font-weight: 300;
            }
            .value {
                margin-left: 4px;
            }
        }
    }
</style>