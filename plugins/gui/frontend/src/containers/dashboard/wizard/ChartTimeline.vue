<template>
    <div class="x-chart-metric">
        <h5 class="grid-span3">Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name" placeholder="query..." />
            <div @click="removeView(index)" class="x-btn link" v-if="index > 0">x</div><div v-else></div>
        </template>
        <a @click="addView" class="x-btn light grid-span3" :class="{ disabled: hasMaxViews }" :title="addBtnTitle">+</a>
        <label>Show Results From</label>
        <div class="line-range grid-span2">
            <x-date-edit v-model="config.dateFrom" />
            <label>to</label>
            <x-date-edit v-model="config.dateTo" />
        </div>
        <label>Group Results By</label>
        <x-select :options="groupOptions" v-model="config.groupBy" class="grid-span2" />
    </div>
</template>

<script>
    import xSelect from '../../../components/inputs/Select.vue'
    import xSelectSymbol from '../../../components/inputs/SelectSymbol.vue'
    import xDateEdit from '../../../components/controls/string/DateEdit.vue'
    import ChartMixin from './chart'

    const dashboardView = { name: '', entity: '' }
    export default {
        name: "x-chart-timeline",
        mixins: [ ChartMixin ],
        components: { xSelect, xSelectSymbol, xDateEdit },
        props: { value: {}, views: { required: true }, entities: { required: true } },
        computed: {
            groupOptions() {
                return [
                    { title: 'Day', name: 'day' },
                    { title: 'Week', name: 'week' },
                    { title: 'Month', name: 'month' }
                ]
            }
        },
        data() {
            return {
                config: {
                    views: [ { ...dashboardView } ],
                    dateFrom: null, dateTo: null, groupBy: ''
                },
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
                this.$emit('validate', !this.config.views.filter(view => view.name === '').length)
            }
        }
    }
</script>

<style lang="scss">
    .x-chart-metric {
        .line-range {
            display: flex;
            justify-content: space-between;
            .cov-vue-date {
                width: 240px;
                .cov-datepicker {
                    width: calc(100% - 4px);
                }
            }
        }
    }
</style>