<template>
    <x-card :title="title" class="x-data-discovery-card" :class="{double: dataCounters && dataCounters.length > 5}" >
        <div class="data-discovery">
            <x-histogram :data="dataCounters" @click-one="runAdaptersFilter" type="logo" :limit="15" />
            <div class="discovery-summary">
                <div class="summary-row">
                    <div class="title">Total seen {{ module }}</div>
                    <div class="quantity">{{ dataSeen }}</div>
                </div>
                <div class="arrow">Axonius Correlation Process</div>
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
			title() {
				return `${this.module} Discovery`
            },
            dataCounters() {
				if (!this.data || !this.data.adapter_count) return []
				return [ ...this.data.adapter_count ].sort((first, second) => second.value - first.value)
            },
            dataSeen() {
				return this.data.total_gross || 0
            },
            dataUnique() {
				return Math.min(this.data.total_net || 0, this.dataSeen)
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
                border-top: 1px solid $theme-orange;
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
                    padding: 8px;
                    width: 180px;
                    position: relative;
                    text-align: center;
                    background-color: $theme-orange;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 400;
                    &:after {
                        content: '';
                        position: absolute;
                        border-right: 98px solid transparent;
                        border-top: 8px solid $theme-orange;
                        border-left: 98px solid transparent;
                        left: 0;
                        bottom: -8px;
                    }
                }
            }
        }
    }
</style>