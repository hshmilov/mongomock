<template>
    <div class="x-chart-metric">
        <h5 class="grid-span3">Select up to {{ max }} queries for comparison:</h5>
        <template v-for="view, index in config.views">
            <x-select-symbol :options="entities" v-model="view.entity" type="icon" placeholder="module..."/>
            <x-select :options="views[view.entity] || []" :searchable="true" v-model="view.name" placeholder="query..." />
            <div @click="removeView(index)" class="x-btn link" v-if="index > 1">x</div><div v-else></div>
        </template>
        <a @click="addView" class="x-btn light grid-span3" :class="{disabled: hasMaxViews}" :title="addBtnTitle">+</a>
    </div>
</template>

<script>
	import xSelect from '../../../components/inputs/Select.vue'
	import xSelectSymbol from '../../../components/inputs/SelectSymbol.vue'
	import ChartMixin from './chart'

	const dashboardView = { name: '', entity: '' }
	export default {
		name: 'x-chart-compare',
        components: { xSelect, xSelectSymbol },
		mixins: [ ChartMixin ],
        props: { value: {}, views: { required: true }, entities: { required: true } },
        data() {
			return {
				config: { views: [ { ...dashboardView }, { ...dashboardView } ] },
                max: 5
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

</style>