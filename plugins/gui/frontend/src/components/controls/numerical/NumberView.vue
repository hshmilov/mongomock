<template>
    <div :class="severity">{{ processedData }}{{ isPercentage && processedData? '%': ''}}</div>
</template>

<script>
	import { mapState } from 'vuex'
    
	export default {
		name: 'x-number-view',
        props: ['schema', 'value'],
        computed: {
			...mapState({
				percentageThresholds(state) {
                    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) {
                        return []
                    }
                    return state.configuration.data.system.percentageThresholds
				}
			}),
			processedData() {
                if (Array.isArray(this.value)) {
                	return this.value.map(item => this.format(item)).join(', ')
                }
                return this.format(this.value)
            },
			isPercentage() {
				return this.schema.format && this.schema.format === 'percentage'
			},
			severity() {
				if (this.value === undefined || this.value === null || !this.isPercentage) return ''

                let minDiff = 101
                let minSeverity = ''
				Object.keys(this.percentageThresholds).forEach(thresholdName => {
					if (this.percentageThresholds[thresholdName] < this.value) return
					let diff = this.percentageThresholds[thresholdName] - this.value
					if (diff < minDiff) {
						minDiff = diff
                        minSeverity = thresholdName
                    }
				})
                return minSeverity
			}
        },
        methods: {
			format(value) {
				if (typeof value === 'number') {
					return value.toFixed(2)
				}
				return ''
            }
        }
	}
</script>

<style lang="scss">

</style>