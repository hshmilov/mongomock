<template>
    <div class="x-historical-date-picker">
        <div class="title">Showing Results for</div>
        <md-datepicker v-model="selectedDate" :md-disabled-dates="checkDateAvailability" :md-immediately="true"
                       @md-clear="onClear" :md-debounce="500" :class="{'no-icon': minimal}" />
    </div>
</template>


<script>
    import { mapState } from 'vuex'

    export default {
        name: 'x-historical-date-picker',
        props: ['module', 'minimal'],
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
            showingHistorical() {
                return this.date != null
            },
            currentDate() {
                return new Date()
            }
        },
        data() {
            return {
                selectedDate: null
            }
        },
        watch: {
            selectedDate(newDate) {
                this.$emit('input', newDate)
            }
        },
        methods: {
            checkDateAvailability(date) {
                if (date < this.firstHistoricalDate || date > this.currentDate) return true

                if (this.allowedDates && !this.allowedDates[date.toISOString().substring(0,10)]) return true

                return false
            },
            onClear() {
                this.$emit('input', null)
                this.$emit('clear')
            }
        }
    }
</script>


<style lang="scss">
    .x-historical-date-picker {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        .title {
            color: $theme-orange;
            font-weight: 300;
            margin-right: 12px;
            line-height: 36px;
        }
        .md-field {
            width: auto;
            padding-top: 0;
            min-height: auto;
            margin-bottom: 0;
        }
        .x-btn.link {
            padding: 2px 0;
            margin-left: -8px;
        }
    }
</style>