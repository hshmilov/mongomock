<template>
    <div class="array inline" :title="allItems">
        <div class="item" v-for="item in limitedItems" v-if="!empty(processedData[item.name])">
            <component :is="item.type" :schema="item" :value="processedData[item.name]"/>
        </div>
        <div class="item" v-if="limit && filteredItems.length > limit">+{{remainder}}</div>
    </div>
</template>

<script>
	import string from '../string/StringView.vue'
	import number from '../numerical/NumberView.vue'
	import integer from '../numerical/IntegerView.vue'
	import array from '../array/ArrayInlineView.vue'
	import bool from '../boolean/BooleanView.vue'
	import file from './FileView.vue'

	import ArrayMixin from './array'

	export default {
		name: 'array',
		mixins: [ArrayMixin],
		components: { string, number, integer, bool, file, array },
		props: { },
        computed: {
            filteredItems() {
                return this.schemaItems.filter(item => !this.empty(this.processedData[item.name]))
            },
			limit() {
                if (this.$parent && this.$parent.schema && this.$parent.schema.type === 'array') {
                    return 10000
                }
				if (this.filteredItems.length && this.filteredItems[0].format === 'logo') {
					return 8
                }
                return 2
            },
            processedData() {
				if (this.isOrderedObject) return this.data
				let items = Object.values(this.data)
                if (this.schema.sort) {
					items.sort()
                }
                if (this.schema.unique) {
					items = Array.from(new Set(items))
                }
                return { ...items }
            },
			limitedItems() {
				if (!this.filteredItems || !this.limit || (this.filteredItems.length <= this.limit)) {
					return this.filteredItems
				}
                return this.filteredItems.slice(0, this.limit)
            },
            allItems() {
				if (Array.isArray(this.processedData)) return this.processedData.join(',')
				return Object.values(this.processedData).join(',')
            },
            remainder() {
			    return this.filteredItems.length - this.limit
            }
        }
	}
</script>

<style lang="scss">

    .array.inline {
        display: flex;
       .item {
           margin-right: 8px;
           line-height: 24px;
        }
    }
</style>
