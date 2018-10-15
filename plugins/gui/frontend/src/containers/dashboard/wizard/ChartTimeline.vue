<template>
    <div class="x-chart-metric">
        <h5 class="grid-span3">Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name" placeholder="query..." />
            <div @click="removeView(index)" class="x-btn link" v-if="index > 0">x</div><div v-else></div>
        </template>
        <a @click="addView" class="x-btn light grid-span3" :class="{ disabled: hasMaxViews }" :title="addBtnTitle">+</a>
        <div class="line-range grid-span3">
            <input type="radio" v-model="rangeType" value="constant" />
            <label>Show Results From Range of Dates</label>
            <template v-if="rangeType === 'constant'">
                <x-date-edit v-model="config.datefrom" :show-time="false" :limit="firstDateLimit" placeholder="from" />
                <x-date-edit v-model="config.dateto" :show-time="false" :limit="firstDateLimit" placeholder="to" />
            </template>
        </div>
    </div>
</template>

<script>
    import xSelect from '../../../components/inputs/Select.vue'
    import xSelectSymbol from '../../../components/inputs/SelectSymbol.vue'
    import xDateEdit from '../../../components/controls/string/DateEdit.vue'
    import ChartMixin from './chart'

    import { mapState } from 'vuex'

    const dashboardView = { name: '', entity: '' }
    export default {
        name: "x-chart-timeline",
        mixins: [ ChartMixin ],
        components: { xSelect, xSelectSymbol, xDateEdit },
        props: { value: {}, views: { required: true }, entities: { required: true } },
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
                    return state.constants.firstHistoricalDate
                }
            }),
            firstDateLimit() {
                return [{ type: 'fromto', from: this.firstHistoricalDate, to: new Date()}]
            }
        },
        data() {
            return {
                config: {
                    views: [ { ...dashboardView } ],
                    datefrom: null, dateto: null
                },
                rangeType: 'constant',
                max: 3
            }
        },
        methods: {
            removeView(index) {
                this.config.views = this.config.views.filter((item, i) => i !== index)
            },
            addView() {
                if (this.hasMaxViews) return
                this.config.views.push({ ...dashboardView })
            },
            validate() {
                this.$emit('validate', !this.config.views.filter(view => view.name === '').length
                    && this.config.datefrom !== null && this.config.dateto !== null)
            }
        }
    }
</script>

<style lang="scss">
    .x-chart-metric {
        .line-range {
            display: grid;
            grid-template-columns: 20px 240px auto auto;
            .cov-vue-date {
                width: 200px;
                .cov-datepicker {
                    width: calc(100% - 4px);
                }
            }
        }
    }
</style>