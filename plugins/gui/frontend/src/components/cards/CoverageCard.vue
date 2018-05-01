<template>
    <x-card :title="`${title} Coverage`" :key="title" class="coverage">
        <x-pie-chart :data="pieSlices" @click-one="$emit('click-one', $event)" />
    </x-card>
</template>

<script>
	import xCard from '../../components/cards/Card.vue'
    import xPieChart from '../charts/Pie.vue'

    const quarters = ['', 'under a quarter', 'under half', 'over half', 'over three quarters']
	export default {
		name: 'coverage-card',
        components: { xCard, xPieChart },
        props: {portion: {required: true}, title: {}, description: {}},
        computed: {
			quarter() {
				return Math.ceil(this.portion * 4)
            },
            quarterMessage() {
                if (!this.quarter) return ''

                return `Coverage level is ${quarters[this.quarter]}`
            },
			pieSlices() {
                return [{
                	portion: 1 - this.portion, class: 'theme-fill-gray-light',  title: this.description
                }, {
                	portion: this.portion, anotate: true, title: this.quarterMessage,
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
                background-color: $grey-1;
                text-transform: uppercase;
            }
        }
        .pie {
            height: 240px;
        }
    }
</style>