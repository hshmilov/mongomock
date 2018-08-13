<template>
    <div class="x-summary-chart" :class="{updating: enumerating}">
        <template v-for="item, index in displayData">
            <component v-if="item.schema" :is="processType(item.schema)" :schema="item.schema" :value="item.value"
                       class="summary" @click="$emit('click-one', index)" />
            <div v-else class="summary" @click="$emit('click-one', index)">{{ item.value }}</div>
            <div class="title">{{ item.name }}</div>
        </template>
    </div>
</template>

<script>
    import string from '../controls/string/StringView.vue'
    import number from '../controls/numerical/NumberView.vue'
	import integer from '../controls/numerical/IntegerView.vue'

	export default {
		name: 'x-summary-chart',
        components: { string, number, integer },
        props: { data: {required: true}},
        data() {
			return {
			    displayData: [ ...this.data ],
                enumerating: false
            }
        },
        watch: {
			data() {
                this.enumerating = true
            }
        },
        methods: {
			processType(schema) {
				if (schema.format && schema.format === 'percentage') {
					return 'integer'
                }
                return schema.type
            }
        },
        updated() {
			if (!this.enumerating) return
            setTimeout(() => {
                this.enumerating = false
                this.displayData = this.displayData.map((item, index) => {
                    let jumpValue = Math.max(10, Math.ceil(this.data[index].value / 200))
                    if (item.value === this.data[index].value) return item
                    this.enumerating = true
                    if (this.data[index].value > item.value) {
                        return { ...item, value: Math.min(item.value + jumpValue,  this.data[index].value)}
                    }
                    // Smaller - need to subtract
					return { ...item, value: Math.max(item.value - jumpValue,  this.data[index].value)}
                })
            }, 10)
        }
	}
</script>

<style lang="scss">
    .x-summary-chart {
        display: grid;
        grid-template-columns: 1fr 2fr;
        .summary {
            font-size: 60px;
            display: inline;
            color: $theme-blue;
            opacity: 0.6;
            cursor: pointer;
            &:hover {
                opacity: 1;
            }
            &.success {
                color: $indicator-success;
            }
            &.warning {
                color: $indicator-warning;
            }
            &.error {
                color: $indicator-error;
            }
        }
        .title {
            display: inline-block;
            max-width: 160px;
            text-align: left;
            margin: auto;
            margin-left: 12px;
            text-transform: capitalize;
        }
    }
</style>