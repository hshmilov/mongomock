<template>
  <div class="x-action-result">
    <template v-if="schema && schema.type">
      <h4 class="title">Configuration</h4>
      <x-array-view
        v-if="schema"
        :schema="schema"
        :value="data.action.config"
      />
    </template>
    <h4 class="title">Results</h4>
    <div
      v-if="isResultAlertAction"
      class="result-container"
    >
      <svg-icon
        :name="`symbol/${alertStatus}`"
        :original="true"
        height="20px"
      />
      <div
        class="result"
        @click="$emit('click-one', alertStatus == 'success' ? 0 : 1)"
      >{{ alertStatusMessage }}</div>
    </div>
    <x-summary
      v-else-if="resultData"
      :data="resultData"
      @click-one="$emit('click-one', $event)"
    />
    <div v-else>Not ran</div>
  </div>
</template>

<script>
  import xSummary from '../../axons/charts/Summary.vue'
  import xArrayView from '../../neurons/schema/types/array/ArrayView.vue'
  import actionsMixin from '../../../mixins/actions'

  export default {
    name: 'XActionResult',
    components: {
      xArrayView, xSummary
    },
    mixins: [actionsMixin],
    props: {
      data: {
        type: Object,
        required: true
      }
    },
    computed: {
      schema () {
        if (!Object.keys(this.actionsDef).length || !this.data || !this.data.action) return {}

        return this.actionsDef[this.data.action['action_name']].schema
      },
      isResultAlertAction () {
        return this.data.action.action_type === 'alert'
      },
      alertStatus () {
        if (this.data.action.results.successful_entities.length > 0) return 'success'
        return 'error'
      },
      alertStatusMessage () {
        return this.data.action.results.message_state
      },
      successEntities () {
        if (!this.data.action.results) return []
        return this.data.action.results['successful_entities']
      },
      failureEntities () {
        if (!this.data.action.results) return []
        return this.data.action.results['unsuccessful_entities']
      },
      resultData () {
        if (!this.successEntities.length && !this.failureEntities.length) return null
        return [{
          name: 'Entities Succeeded',
          value: this.successEntities.length
        }, {
          name: 'Entities Failed',
          value: this.failureEntities.length
        }]
      }
    }
  }
</script>

<style lang="scss">
    .x-action-result {
        overflow: auto;
        display: grid;
        grid-template-rows: 48px min-content 48px min-content;
        align-items: flex-end;
        > .title {
            margin-bottom: 12px;

            &:first-child {
                margin-top: 0;
            }
        }

        .x-array-view {
            max-height: 60vh;
            overflow: auto;
        }

        .result-container {
            display: flex;
            .svg-icon {
                margin-right: 4px;
            }
            .result {
                white-space: pre-wrap;
                width: calc(100% - 24px);
                margin-left: 8px;
            }
        }
        .x-summary {
            grid-template-columns: min-content auto;
            grid-gap: 8px;

            .summary:first-child {
                color: $indicator-success;
            }

            .summary {
                color: $indicator-error;
            }

            .title {
                font-size: 16px;
            }
        }
    }
</style>