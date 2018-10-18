<template>
    <div class="x-chart-metric">
        <md-switch v-model="config.intersection" class="md-primary">{{ isIntersection? 'Intersection' : 'Comparison'}}</md-switch>
        <h5 class="grid-span3" v-if="isIntersection">Select a base query and another one to intersect with it:</h5>
        <h5 class="grid-span3" v-else>Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="Module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name" placeholder="Query..." />
            <div @click="removeView(index)" class="x-btn link" v-if="index > 0">x</div><div v-else></div>
        </template>
        <a @click="addView" class="x-btn light grid-span3" :class="{ disabled: hasMaxViews }" :title="addBtnTitle">+</a>
        <div class="line-range grid-span3">
            <input type="radio" v-model="config.timeframe.type" value="absolute" id="range_absolute" />
            <label for="range_absolute">Show results from range of dates</label>
            <template v-if="isRangeAbsolute">
                <x-date-edit v-model="config.timeframe.from" :show-time="false" :limit="fromDateLimit" placeholder="From" />
                <x-date-edit v-model="config.timeframe.to" :show-time="false" :limit="toDateLimit" placeholder="To" />
            </template>
            <div class="grid-span2" v-else ></div>
            <input type="radio" v-model="config.timeframe.type" value="relative" id="range_relative" />
            <label for="range_relative">Show results in the last</label>
            <template v-if="!isRangeAbsolute">
                <input type="number" value="config.timeframe.count" @input="updateTimeframeCount" >
                <x-select :options="relativeRangeUnits" v-model="config.timeframe.unit" placeholder="Units" />
            </template>
            <div class="grid-span2" v-else ></div>
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
        components: {
            xSelect, xSelectSymbol, xDateEdit },
        props: { value: {}, views: { required: true }, entities: { required: true } },
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
                    return state.constants.firstHistoricalDate
                }
            }),
            firstDateLimit() {
                return [{ type: 'fromto', from: this.firstHistoricalDate, to: new Date()}]
            },
            fromDateLimit() {
                if (!this.config.timeframe.to) {
                    return this.firstDateLimit
                }
                return [{ type: 'fromto', from: this.firstHistoricalDate, to: this.config.timeframe.to}]
            },
            toDateLimit() {
                if (!this.config.timeframe.from) {
                    return this.firstDateLimit
                }
                return [{ type: 'fromto', from: this.config.timeframe.from, to: new Date()}]
            },
            relativeRangeUnits() {
                return [
                    { name: 'day', title: 'Days' },
                    { name: 'week', title: 'Weeks' },
                    { name: 'month', title: 'Months' },
                    { name: 'year', title: 'Years' }
                ]
            },
            isRangeAbsolute() {
                return this.config.timeframe.type === 'absolute'
            },
            isIntersection() {
                return this.config.intersection
            },
            absoluteRangeValid() {
                return this.config.timeframe.from != null && this.config.timeframe.to !== null
            },
            relativeRangeValid() {
                return this.config.timeframe.count > 0 && this.config.timeframe.unit
            }
        },
        data() {
            return {
                config: {
                    views: [ { ...dashboardView } ],
                    timeframe: {
                        type: 'absolute', from: null, to: null
                    },
                    intersection: false
                },
                max: 3
            }
        },
        watch: {
            isRangeAbsolute() {
                if (this.isRangeAbsolute) {
                    this.config.timeframe = {
                        type: 'absolute', from: null, to: null
                    }
                } else {
                    this.config.timeframe = {
                        type: 'relative', unit: 'day', count: 7
                    }
                }
            },
            isIntersection() {
                this.max = (this.config.intersection)? 2 : 3
            }
        },
        methods: {
            updateTimeframeCount(value) {
               this.config.timeframe.count = parseInt(value.data)
            },
            removeView(index) {
                this.config.views = this.config.views.filter((item, i) => i !== index)
            },
            addView() {
                if (this.hasMaxViews) return
                this.config.views.push({ ...dashboardView })
            },
            validate() {
                this.$emit('validate', !this.config.views.filter(view => view.name === '').length
                    && (this.absoluteRangeValid || this.relativeRangeValid))
            }
        }
    }
</script>

<style lang="scss">
    .x-chart-metric {
        .line-range {
            display: grid;
            grid-template-columns: 20px 240px auto auto;
            grid-gap: 8px;
            align-items: center;
            grid-template-rows: 32px;
            .cov-vue-date {
                width: 200px;
                .cov-datepicker {
                    width: calc(100% - 4px);
                }
            }
            .x-select-trigger {
                line-height: 24px;
                height: 24px;
            }
        }
    }
</style>