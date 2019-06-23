<template>
    <div class="x-historical-date">
        <x-date-edit :value="value" @input="onInput" :check-disabled="isDateUnavailable" label="Display by Date"/>
    </div>
</template>


<script>
    import xDateEdit from '../schema/types/string/DateEdit.vue'
    import {mapState, mapActions} from 'vuex'

    export default {
        name: 'x-historical-date',
        components: {
            xDateEdit
        },
        props: ['value', 'module'],
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
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
                allowedDates(state) {
                    return state.constants.allowedDates[this.module]
                }
            }),
            currentDate() {
                return new Date()
            }
        },
        methods: {
            isDateUnavailable(date) {
                if (date < this.firstHistoricalDate || date > this.currentDate) return true

                if (this.allowedDates && !this.allowedDates[date.toISOString().substring(0, 10)]) return true

                return false
            },
            onInput(historical) {
                this.$emit('input', historical)
            }
        },
    }
</script>


<style lang="scss">
    .x-historical-date {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        overflow: hidden;

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