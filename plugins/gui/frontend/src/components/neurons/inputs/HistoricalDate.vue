<template>
  <div class="x-historical-date">
    <x-date-edit
      ref="date"
      :value="value"
      :check-disabled="isDateUnavailable"
      :hide="hide"
      label="Display by Date"
      @input="onInput"
    />
  </div>
</template>


<script>
  import xDateEdit from '../schema/types/string/DateEdit.vue'
  import { mapState } from 'vuex'

  export default {
    name: 'XHistoricalDate',
    components: {
      xDateEdit
    },
    props: {
      value: {
        type: [String, Date],
        default: null
      },
      module: {
        type: String,
        default: ''
      },
      hide: {
        type: Boolean,
        default: false
      }
    },
    computed: {
      ...mapState({
        firstHistoricalDate (state) {
          let historicalDate = null
          if (this.module) {
            historicalDate = state.constants.firstHistoricalDate[this.module]
          } else {
            historicalDate = Object.values(state.constants.firstHistoricalDate).reduce((a, b) => {
              return (new Date(a) < new Date(b)) ? a : b
            }, new Date())
          }
          historicalDate = new Date(historicalDate)
          historicalDate.setDate(historicalDate.getDate() - 1)
          return historicalDate
        },
        allowedDates (state) {
          return state.constants.allowedDates[this.module]
        }
      }),
      currentDate () {
        return new Date()
      }
    },
    methods: {
      isDateUnavailable (date) {
        if (date < this.firstHistoricalDate || date > this.currentDate) return true

        return (this.allowedDates && !this.allowedDates[date.toISOString().substring(0, 10)])
      },
      onInput (historical) {
        if (historical && this.isDateUnavailable(new Date(historical))) {
          this.$refs.date.onClear()
        } else {
          this.$emit('input', historical)
        }
      }
    }
  }
</script>


<style lang="scss">
    .x-historical-date {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        overflow: hidden;

        .md-datepicker {
            margin: -20px 0 0 0;
            min-height: auto;

            .md-input {
                max-width: 160px;
            }
        }
    }
</style>