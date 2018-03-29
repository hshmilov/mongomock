<template>
    <x-card :title="`${title} Coverage`" :key="title" class="coverage">
        <div class="coverage-status">
            <div class="text">Consider installing {{title}} system on uncovered devices</div>
            <div :class="`mark indicator-border-${quarter}`">{{quarterText[quarter]}}</div>
        </div>
        <x-pie-chart :data="pieSlices" @click-slice="$emit('click-slice', $event)" :tooltip="tooltip" />
    </x-card>
</template>

<script>
	import xCard from '../../components/cards/Card.vue'
    import xPieChart from '../charts/Pie.vue'

	export default {
		name: 'coverage-pie',
        components: { xCard, xPieChart },
        props: {portion: {required: true}, title: {}},
        computed: {
			quarter() {
				return Math.ceil(this.portion * 4)
            },
            quarterText() {
				return ['None', 'Poor', 'Low', 'Average', 'Good']
            },
			pieSlices() {
                return [{
					portion: 1 - this.portion, class: 'theme-fill-gray-light'
                }, {
					portion: this.portion, percentage: Math.round(this.portion * 100),
                    class: `indicator-fill-${this.quarter}`
                }]
			}
        }
	}
</script>

<style lang="scss">
    .coverage {
        .coverage-status {
            display: flex;
            flex-direction: row;
            .text {
                font-size: 12px;
            }
            .mark {
                align-self: center;
                margin-left: 8px;
                line-height: 30px;
                padding: 0 4px;
                border-width: 1px;
                border-style: solid;
                border-radius: 12px;
                background-color: $theme-gray-light;
                text-transform: uppercase;
            }
        }
        .pie {
            height: 240px;
        }
    }
</style>