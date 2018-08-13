<template>
    <x-card :title="title" class="x-data-discovery-card" :class="{double: dataCounters && dataCounters.length > 5}" >
        <div class="data-discovery">
            <x-histogram :data="dataCounters" @click-one="runAdaptersFilter" type="logo" :limit="15" />
            <div class="discovery-summary">
                <div class="summary-row">
                    <div class="title">Total {{ module }} seen</div>
                    <div class="quantity">{{ dataSeen }}</div>
                </div>
                <div class="arrow">Axonius {{ singularModule }} Correlation</div>
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
				return [ ...this.data.counters ].sort((first, second) => second.value - first.value)
            },
            dataSeen() {
				return this.data.seen || 0
            },
            dataUnique() {
				return Math.min(this.data.unique || 0, this.dataSeen)
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
                    }
                    .quantity {
                        font-weight: 500;
                    }
                }
                .arrow {
                    margin: auto;
                    margin-top: 8px;
                    margin-bottom: 16px;
                    padding: 4px 0;
                    width: 180px;
                    position: relative;
                    text-align: center;
                    background-color: $theme-orange;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 400;
                    text-transform: capitalize;
                    &:after {
                        content: '';
                        position: absolute;
                        border-right: 90px solid transparent;
                        border-top: 12px solid $theme-orange;
                        border-left: 90px solid transparent;
                        left: 0;
                        bottom: -12px;
                    }
                }
            }
        }
    }
</style>