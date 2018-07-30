<template>
    <div class="x-prescription-bolus">
        <x-array-view :schema="detailsSchema" :value="details" />
        <x-trend v-if="details.trend" :value="details.trend" />
    </div>
</template>

<script>
    import xArrayView from '../../controls/array/ArrayView.vue'
    import xTrend from '../../patterns/Trend.vue'

	export default {
		name: 'prescription-bolus',
        components: { xArrayView, xTrend },
        props: { data: { required: true }},
        computed: {
			detailsSchema() {
				return {
					type: 'array', items: [
                        { type: 'number', name: 'bolus_volume', title: 'Bolus Volume' },
						{ type: 'integer', name: 'number_of_boluses_exists', title: 'No. of Existing Boluses' },
						{ type: 'integer', name: 'requested_boluses', title: 'No. of Requested Boluses' },
						{ type: 'integer', name: 'given_boluses', title: 'No. of Given Boluses' },
						{ type: 'string', name: 'instance_state', title: 'Bolus State' },
                    ]
                }
			},
            details() {
				if (!this.data || !this.data.instance_details || !this.data.instance_details.length) return {}

				return this.data.instance_details[0]
            }
        }
	}
</script>

<style lang="scss">
    .x-prescription-bolus {
        display: flex;
        flex-direction: column;
        .x-array-view {
            flex: 1 0 auto;
        }
    }
</style>