<template>
    <div class="x-chart-metric">
        <h5 class="grid-span3">Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name"
                      placeholder="query..."/>
            <x-button link @click="removeView(index)" v-if="index > 1">x</x-button>
            <div v-else></div>
        </template>
        <x-button light @click="addView" class="grid-span3" :disabled="hasMaxViews" :title="addBtnTitle">+</x-button>
    </div>
</template>

<script>
    import xSelect from '../../axons/inputs/Select.vue'
    import xButton from '../../axons/inputs/Button.vue'
    import xSelectSymbol from '../../neurons/inputs/SelectSymbol.vue'
    import chartMixin from './chart'

    const dashboardView = {name: '', entity: ''}
    export default {
        name: 'x-chart-compare',
        components: {xButton, xSelect, xSelectSymbol},
        mixins: [chartMixin],
        props: {value: {}, views: {required: true}, entities: {required: true}},
        data() {
            return {
                config: {views: [{...dashboardView}, {...dashboardView}]},
                max: 5
            }
        },
        methods: {
            removeView(index) {
                this.config.views = this.config.views.filter((item, i) => i !== index)
            },
            addView() {
                this.config.views.push({...dashboardView})
            },
            validate() {
                this.$emit('validate', !this.config.views.filter(view => view.name === '').length)
            }
        }
    }
</script>

<style lang="scss">

</style>