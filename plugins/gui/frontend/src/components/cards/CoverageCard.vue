<template>
    <x-card :title="`${data.title} Coverage`" class="coverage">
        <x-pie-chart :data="pieSlices" @click-one="$emit('click-one', $event)" :id="data.name" :force-text="true"
                     :read-only="readOnly" />
    </x-card>
</template>

<script>
	import xCard from '../../components/cards/Card.vue'
    import xPieChart from '../charts/Pie.vue'

    const quarters = ['', 'under a quarter', 'under half', 'over half', 'over three quarters']
	export default {
		name: 'coverage-card',
        components: { xCard, xPieChart },
        props: { data: {}, readOnly: { default: false } },
        computed: {
			quarter() {
				return Math.ceil(this.data.portion * 4)
            },
            quarterMessage() {
                if (!this.quarter) return ''

                return `Coverage level is ${quarters[this.quarter]}`
            },
			pieSlices() {
                return [{
                	value: 0, name: `${this.data.title} Coverage`
                }, {
                	value: 1 - this.data.portion,  name: 'Uncovered Devices', class: 'theme-fill-gray-light',
                    description: this.data.description
                }, {
                	value: this.data.portion, name: this.quarterMessage, class: `indicator-fill-${this.quarter}`
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