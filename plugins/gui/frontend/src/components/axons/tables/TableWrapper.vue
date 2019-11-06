<template>
  <div class="x-table-wrapper">
    <div
      v-if="loading"
      class="v-spinner-bg"
    />
    <pulse-loader
      :loading="loading"
      color="#FF7D46"
    />
    <slot name="search" />
    <div class="table-header">
      <div
        v-if="title"
        class="table-title"
      >
        <div class="text">{{ title }}</div>
        <div
          v-if="count !== undefined"
          class="table-title count"
        >({{ count }})</div>
        <slot name="state" />
      </div>
      <div class="table-error">{{ error }}</div>
      <div class="actions">
        <slot name="actions" />
      </div>
    </div>
    <slot name="table" />
  </div>
</template>

<script>
  import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

  export default {
    name: 'XTableWrapper',
    components: { PulseLoader },
    props: {
      title: {
        type: String,
        required: true
      },
      loading: {
        type: Boolean,
        default: false
      },
      count: {
        type: [Number, String],
        default: undefined
      },
      error: {
        type: String,
        default: ''
      }
    },
    data () {
      return {
        searchValue: ''
      }
    }
  }
</script>

<style lang="scss">
    .x-table-wrapper {
        height: calc(100% - 30px);
        background: $theme-white;
        position: relative;

        .table-header {
            display: flex;
            padding: 8px 0;
            line-height: 24px;
            background: $grey-0;
            align-items: flex-end;

            .table-title {
                display: flex;
                line-height: 30px;

                .text {
                    font-weight: 400;
                }

                .count {
                    margin-left: 8px;
                }
            }

            .table-error {
                flex: 1 0 auto;
                color: $indicator-error;
                display: inline-block;
                margin-left: 24px;
                font-size: 12px;
                white-space: pre;
            }

            .actions {
                display: grid;
                grid-auto-flow: column;
                grid-template-columns: max-content;
                grid-gap: 0 8px;
            }
        }
    }
</style>