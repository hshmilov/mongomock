<template>
    <x-card :title="title" class="x-data-discovery-card" :class="{double: dataCounters && dataCounters.length > 5}" >
        <div class="data-discovery">
            <x-histogram :data="dataCounters" type="logo" :limit="15" @click-one="runAdaptersFilter" :read-only="!filter" />
            <div class="discovery-summary">
                <div class="summary-row">
                    <div class="title">Total {{ module }} seen</div>
                    <div class="quantity">{{ dataSeen }}</div>
                </div>
                <div class="summary-row">
                    <div class="title mid">Axonius {{ singularModule }} Correlation</div>
                    <div class="quantity">
                        <svg-icon name="symbol/funnel" :original="true" width="48" height="48" />
                    </div>
                </div>
                <div class="summary-row">
                    <div class="title">Total unique {{ module }}</div>
                    <div class="quantity">{{ dataUnique }}</div>
                </div>
            </div>
        </div>
    </x-card>
</template>

<script>
	import xCard from '../../components/cards/Card.vue'
    import xHistogram from '../charts/Histogram.vue'

	export default {
		name: 'x-entity-discovery-card',
        components: { xCard, xHistogram },
        props: { data: { required: true }, module: { required: true }, filter: { } },
        computed: {
			singularModule() {
				return this.module.slice(0, this.module.length - 1)
            },
			title() {
				return `${this.singularModule} Discovery`
            },
            dataCounters() {
				if (!this.data || !this.data.counters) return []

                function pretty_number(a, b) {
				    if (a != b){
				        return `${a} (${b})`
                    }
                    return a
                }

				return [ ...this.data.counters ]
                    .sort((first, second) => second.value[1] - first.value[1])
                    .map(x => {
                        return {
                            name: x.name,
                            value:`${pretty_number(x.value[0], x.value[1])}`
                        }
                    })
            },
            dataSeen() {
			    let seen = this.data.seen || 0
                let nonunique_seen = this.data.nonunique_seen || 0
                if (seen != nonunique_seen) {
                    return `${seen} (${nonunique_seen})`
                }
                return seen
            },
            dataUnique() {
				return Math.min(this.data.unique || 0, this.data.seen || 0)
            }
        },
        methods: {
			runAdaptersFilter(index) {
				if (!this.filter) return
				this.filter(`adapters == '${this.dataCounters[index].name}'`, this.module)
			}
        }
	}
</script>

<style lang="scss">
    .x-data-discovery-card {
        &.double {
            grid-row: 1 / span 2;
        }
        .x-title {
            text-transform: capitalize;
        }
        .data-discovery {
            display: flex;
            flex-direction: column;
            .discovery-summary {
                border-top: 2px dashed $grey-2;
                padding-top: 12px;
                margin-top: 12px;
                .summary-row {
                    display: flex;
                    font-size: 18px;
                    .title {
                        flex: auto 1 0;
                        &.mid {
                            font-size: 14px;
                            color: $theme-orange;
                            margin: auto 0;
                            text-transform: capitalize;
                        }
                    }
                    .quantity {
                        font-weight: 500;
                        width: 60px;
                        text-align: center;
                    }
                    .svg-icon {
                        margin: 6px 0;
                        .svg-fill {
                            fill: $theme-orange;
                        }
                    }
                }
            }
        }
    }
</style>