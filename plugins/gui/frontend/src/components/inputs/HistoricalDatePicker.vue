<template>
    <div class="x-historical-date-picker">
        <div class="title">Showing Results for</div>
        <x-date-edit @input="confirmPickDate" placeholder="latest" v-model="date" :show-time="false"
                     :limit="[{ type: 'fromto', from: firstHistoricalDate, to: new Date()}]"/>
        <a v-if="showingHistorical" class="x-btn link" @click="clearDate">x</a>
    </div>
</template>


<script>
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import {mapState} from 'vuex'

    export default {
        name: 'x-historical-date-picker',
        components: {
            xDateEdit
        },
        data() {
            return {
                date: this.value
            }
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
                            return (a < b) ? a : b
                        }, null)
                    }
                    historicalDate = new Date(historicalDate)
                    historicalDate.setDate(historicalDate.getDate() - 1)
                    return historicalDate
                }
            }),
            showingHistorical() {
                return this.date != null
            }
        },
        methods: {
            confirmPickDate() {
                this.$emit('input', this.date)
            },
            clearDate() {
                this.date = null
                this.$emit('input', this.date)
                this.$emit('cleared', null)
            }
        },
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
            line-height: 24px;
        }
        .cov-vue-date {
            width: 200px;
            margin-right: 12px;
            input {
                width: calc(100% - 4px);
            }
        }
        .x-btn.link {
            padding: 2px 0;
            margin-left: -8px;
        }
    }
</style>