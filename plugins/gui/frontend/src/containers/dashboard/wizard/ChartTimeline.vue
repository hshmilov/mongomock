<template>
    <div class="x-chart-metric">
        <md-switch v-model="config.intersection" class="md-primary">{{ isIntersection? 'Intersection' : 'Comparison'}}</md-switch>
        <h5 class="grid-span3" v-if="isIntersection">Select a base query and another one to intersect with it:</h5>
        <h5 class="grid-span3" v-else>Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="Module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name" placeholder="Query..." />
            <div @click="removeView(index)" class="x-btn link" v-if="!isIntersection && index > 0">x</div>
            <div v-else></div>
        </template>
        <button @click="addView" class="x-btn light grid-span3" :class="{ disabled: hasMaxViews }" :title="addBtnTitle">+</button>
        <div class="line-range grid-span3">
            <input type="radio" v-model="config.timeframe.type" value="absolute" id="range_absolute" />
            <label for="range_absolute">Show results in date range</label>
            <template v-if="isRangeAbsolute">
                <x-date-edit v-model="config.timeframe.from" :is-disabled-handler="checkDateAvailabilityFrom"
                             :format="false" :clearable="false" label="From" />
                <x-date-edit v-model="config.timeframe.to" :is-disabled-handler="checkDateAvailabilityTo"
                             :format="false" :clearable="false" label="To" />
            </template>
            <div class="grid-span2" v-else ></div>
            <input type="radio" v-model="config.timeframe.type" value="relative" id="range_relative" />
            <label for="range_relative">Show results in the last</label>
            <template v-if="!isRangeAbsolute">
                <input type="number" v-model.number="config.timeframe.count" @keypress="validateNumber" >
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
        components: { xDateEdit, xSelect, xSelectSymbol },
        props: { value: {}, views: { required: true }, entities: { required: true } },
        computed: {
            ...mapState({
                firstHistoricalDate(state) {
                    return Object.values(state.constants.firstHistoricalDate)
                        .map(dateStr => new Date(dateStr))
                        .reduce((a, b) => {
                            return (a < b) ? a : b
                        }, new Date())
                }
            }),
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
                // Update max allowed queries and required queries
                if (this.config.intersection) {
                    this.max = 2
                    if (this.config.views.length < 2) {
                        this.config.views.push({ ...dashboardView })
                    } else if (this.config.views.length > 2) {
                        this.config.views.splice(2)
                    }
                } else {
                    this.max = 3
                }
            }
        },
        methods: {
            validateNumber(keyEvent) {
                keyEvent = (keyEvent) ? keyEvent : window.event
                let charCode = (keyEvent.which) ? keyEvent.which : keyEvent.keyCode
                if (charCode > 31 && (charCode < 48 || charCode > 57)) {
                    keyEvent.preventDefault()
                } else {
                    return true
                }
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
            },
            checkDateAvailabilityFrom(date) {
                let isPast = date < new Date(this.firstHistoricalDate)
                if (!this.config.timeframe.to) {
                    return isPast || date >= new Date()
                }
                return isPast || date >= this.config.timeframe.to
            },
            checkDateAvailabilityTo(date) {
                let isFuture = date > new Date()
                if (!this.config.timeframe.from) {
                    return date < this.firstHistoricalDate || isFuture
                }
                return date <= this.config.timeframe.from || isFuture
            }
        }
    }
</script>

<style lang="scss">
    .x-chart-metric {
        .line-range {
            display: grid;
            grid-template-columns: 20px 180px auto auto;
            grid-gap: 8px;
            align-items: center;
            grid-template-rows: 32px;
            min-width: 0;
            .x-select-trigger {
                line-height: 24px;
                height: 24px;
            }
        }
    }
</style>