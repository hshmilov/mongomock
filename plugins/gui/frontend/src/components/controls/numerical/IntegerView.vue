<template>
    <div :class="severity">{{ processedData }}{{ isPercentage? '%': ''}}</div>
</template>

<script>
    import { mapState } from 'vuex'

	export default {
		name: 'x-integer-view',
		props: ['schema', 'value'],
		computed: {
            ...mapState({
                percentageThresholds(state) {
                    if (!state.configurable.gui.GuiService || !state.configurable.gui.GuiService.config.system_settings) {
                        return []
                    }
                    return state.configurable.gui.GuiService.config.system_settings.percentageThresholds
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
				if (!this.isPercentage) return ''

				return Object.keys(this.percentageThresholds).find(thresholdName => {
					return (this.percentageThresholds[thresholdName].gte <= this.processedData
						&& this.percentageThresholds[thresholdName].lte >= this.processedData)
				})
			}
		},
		methods: {
			format(value) {
				if (typeof value === 'number') {
					return parseInt(value)
				}
				return ''
			}
		}
	}
</script>

<style lang="scss">

</style>