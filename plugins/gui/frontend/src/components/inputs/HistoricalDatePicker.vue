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
        props: ['value'],
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
                    return state.constants.first_historical_date
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
        .title {
            color: $theme-orange;
            font-weight: 400;
            margin-right: 12px;
            line-height: 30px;
        }
        .cov-vue-date {
            width: 170px;
            margin-right: 16px;
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