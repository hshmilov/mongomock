<template>
    <div class="array inline" :title="allItems">
        <div class="item" v-for="item in limitedItems" v-if="!empty(data[item.name])">
            <component :is="item.type" :schema="item" :value="data[item.name]"/>
        </div>
        <div class="item" v-if="limit && schemaItems.length > limit"
        >+{{schemaItems.length - limit}}</div>
    </div>
</template>

<script>
	import string from '../string/StringView.vue'
	import number from '../numerical/NumberView.vue'
	import integer from '../numerical/IntegerView.vue'
	import bool from '../boolean/BooleanView.vue'
	import file from './FileView.vue'

	import ArrayMixin from './array'

	export default {
		name: 'array',
		mixins: [ArrayMixin],
		components: { string, number, integer, bool, file },
		props: { limit: {} },
        computed: {
			limitedItems() {
				if (!this.schemaItems || !this.limit || (this.schemaItems.length <= this.limit)) {
					return this.schemaItems
				}
                return this.schemaItems.slice(0, this.limit)
            },
            allItems() {
				if (Array.isArray(this.data)) return this.data.join(',')
				return Object.values(this.data).join(',')
            }
        }
	}
</script>

<style lang="scss">

    .array.inline {
        display: flex;
       .item {
           margin-right: 8px;
        }
    }
</style>