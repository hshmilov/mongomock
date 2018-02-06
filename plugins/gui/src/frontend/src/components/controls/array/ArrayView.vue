<template>
    <div class="array">
        <label v-if="schema.title" :title="schema.description || ''" class="label">{{schema.title}}</label>
        <div v-for="item in schemaItems" class="item" v-if="!empty(data[item.name])">
            <div v-if="typeof item.name === 'number'" class="index">{{item.name + 1}}.</div>
            <x-type-wrap :schema="item">
                <component :is="`x-${item.type}-view`" :schema="item" :value="data[item.name]"
                           @input="$emit('input', data)"></component>
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
	import xTypeWrap from './TypeWrap.vue'
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
			xTypeWrap,
			xStringView,
			xNumberView,
			xIntegerView,
			xBoolView,
			xFileView
		}
	}
</script>

<style lang="scss">
    .label {  margin-bottom: 0;  }

    .item {
        margin-bottom: .5rem;
        .index {
            display: inline-block;
            vertical-align: top;
            margin-left: 1rem;
        }
        .object {  display: inline-block;  }
    }
</style>