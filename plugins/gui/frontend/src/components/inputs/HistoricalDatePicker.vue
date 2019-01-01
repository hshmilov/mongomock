<template>
    <div class="x-historical-date-picker">
        <x-date-edit :value="value" @input="onInput" :is-disabled-handler="isDateUnavailable" label="Display by Date" />
    </div>
</template>


<script>
    import { mapState, mapActions } from 'vuex'
    import XDateEdit from '../controls/string/DateEdit.vue'
    import { FETCH_FIRST_HISTORICAL_DATE, FETCH_ALLOWED_DATES } from '../../store/modules/constants'

    export default {
        name: 'x-historical-date-picker',
        components: { XDateEdit },
        props: ['value', 'module'],
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
                    let historicalDate = null
                    if (this.module) {
                        historicalDate = state.constants.firstHistoricalDate[this.module]
                    } else {
                        historicalDate = Object.values(state.constants.firstHistoricalDate).reduce((a, b) => {
                            return (a < b) ? a : b
                        }, null)
                    }
                    historicalDate = new Date(historicalDate)
                    historicalDate.setDate(historicalDate.getDate() - 1)
                    return historicalDate
                },
                allowedDates(state) {
                    return state.constants.allowedDates[this.module]
                }
            }),
            currentDate() {
                return new Date()
            }
        },
        methods: {
            ...mapActions({
                fetchFirstHistoricalDate: FETCH_FIRST_HISTORICAL_DATE, fetchAllowedDates: FETCH_ALLOWED_DATES
            }),
            isDateUnavailable(date) {
                if (date < this.firstHistoricalDate || date > this.currentDate) return true

                if (this.allowedDates && !this.allowedDates[date.toISOString().substring(0,10)]) return true

                return false
            },
            onInput(historical) {
                this.$emit('input', historical)
            }
        },
        created() {
            this.fetchFirstHistoricalDate()
            this.fetchAllowedDates()
        }
    }
</script>


<style lang="scss">
    .x-historical-date-picker {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        .md-datepicker {
            margin-bottom: 0;
            margin-top: -20px;
            margin-right: 8px;
            .md-input {
                max-width: 160px;
            }
        }
    }
</style>