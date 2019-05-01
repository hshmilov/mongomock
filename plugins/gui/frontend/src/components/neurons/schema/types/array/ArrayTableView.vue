<template>
  <div
    class="array inline"
    :title="allItems"
  >
    <div
      v-for="item in limitedItems"
      :key="item.name"
      class="item"
    >
      <component
        :is="item.type"
        :schema="item"
        :value="processedData[item.name]"
      />
    </div>
    <div
      v-if="limit && filteredItems.length > limit"
      class="item"
    >+{{ remainder }}</div>
  </div>
</template>

<script>
	import string from '../string/StringView.vue'
	import number from '../numerical/NumberView.vue'
	import integer from '../numerical/IntegerView.vue'
	import array from './ArrayTableView.vue'
	import bool from '../boolean/BooleanView.vue'
	import file from './FileView.vue'

	import arrayMixin from './array'

	export default {
		name: 'Array',
		components: { string, number, integer, bool, file, array },
		mixins: [arrayMixin],
		props: { },
        computed: {
            filteredItems() {
                return this.schemaItems.filter(item => !this.empty(this.processedData[item.name]))
            },
			limit() {
                if (this.schemaItems.length && this.schemaItems[0].format === 'logo') {
					return null
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
                return items
            },
			limitedItems() {
				if (!this.filteredItems || !this.limit || (this.filteredItems.length <= this.limit)) {
					return this.filteredItems
				}
                return this.filteredItems.slice(0, this.limit)
            },
            remainder() {
			    return this.filteredItems.length - this.limit
            },
            allItems() {
				if (Array.isArray(this.processedData)) return this.processedData.join(',')
				return Object.values(this.processedData).join(',')
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
      display: flex;
      align-items: center;
    }
  }
</style>
