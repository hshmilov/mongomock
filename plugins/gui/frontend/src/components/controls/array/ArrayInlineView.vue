<template>
    <div class="array" :class="{inline: !multiline}" :title="allItems">
        <div class="item" :class="{inline: !multiline}" v-for="item in limitedItems" v-if="!empty(data[item.name])">
            <component :is="`x-${item.type}-view`" :schema="item" :value="data[item.name]"/>
        </div>
        <div class="item" v-if="limit && schemaItems.length > limit"
        >+{{schemaItems.length - limit}}</div>
    </div>
</template>

<script>
	import xStringView from '../string/StringView.vue'
	import xNumberView from '../numerical/NumberView.vue'
	import xIntegerView from '../numerical/IntegerView.vue'
	import xBoolView from '../boolean/BooleanView.vue'
	import xFileView from './FileView.vue'

	import ArrayMixin from './array'

	export default {
		name: 'x-array-view',
		mixins: [ArrayMixin],
		components: {
			xStringView,
			xNumberView,
			xIntegerView,
			xBoolView,
			xFileView
		},
		props: {limit: {}, multiline: {default: false}},
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

<style lang="scss" scoped>

    .array {
        .item {
            margin-bottom: 0;
            margin-right: .5rem;
        }
        &.inline {
            display: flex;
        }
    }
</style>