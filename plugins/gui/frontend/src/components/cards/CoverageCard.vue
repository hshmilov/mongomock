<template>
    <x-card :title="`${nameText} Coverage`" :key="name" class="coverage">
        <div :class="`coverage-status indicator-border-${quarter}`">{{quarterText[quarter]}}</div>
        <x-pie-chart :data="pieSlices" @click-slice="$emit('click', name)" :title="title" />
    </x-card>
</template>

<script>
	import xCard from '../../components/cards/Card.vue'
    import xPieChart from '../charts/Pie.vue'

	export default {
		name: 'coverage-pie',
        components: { xCard, xPieChart },
        props: {portion: {required: true}, name: {}},
        computed: {
			quarter() {
				return Math.ceil(this.portion * 4)
            },
            quarterText() {
				return ['None', 'Poor', 'Low', 'Average', 'Good']
            },
            nameText() {
				return this.name.split('_').join(' ')
            },
			pieSlices() {
                return [{
					portion: 1 - this.portion, class: 'theme-fill-gray-light'
                }, {
					name: this.name, portion: this.portion, class: `indicator-fill-${this.quarter}`
                }]
			},
			title() {
				return `Click to view devices without ${this.nameText} and consider aligning them`
            }
        }
	}
</script>

<style lang="scss">
    .coverage {
        .coverage-status {
            align-self: flex-end;
            line-height: 30px;
            padding: 0 4px;
            border-width: 1px;
            border-style: solid;
            border-radius: 12px;
            background-color: $theme-gray-light;
            text-transform: uppercase;
        }
        .pie {
            height: 240px;
        }
    }
</style>