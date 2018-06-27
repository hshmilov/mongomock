<template>
    <div class="array">
        <div v-if="schema.title === 'SEPARATOR'" class="separator">&nbsp;</div>
        <label v-else-if="schema.title" :title="schema.description || ''" class="label">{{schema.title}}</label>
        <div v-for="item in schemaItems" class="item" v-if="!empty(data[item.name])">
            <div v-if="typeof item.name === 'number'" class="index">{{item.name + 1}}.</div>
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description"
                         :required="true">
                <component :is="item.type" :schema="item" :value="data[item.name]" @input="$emit('input', data)"/>
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
	import xTypeWrap from './TypeWrap.vue'
	import string from '../string/StringView.vue'
	import number from '../numerical/NumberView.vue'
	import integer from '../numerical/IntegerView.vue'
	import bool from '../boolean/BooleanView.vue'
	import file from './FileView.vue'

    import ArrayMixin from './array'

	export default {
		name: 'array',
		mixins: [ArrayMixin],
		components: { xTypeWrap, string, number, integer, bool, file }
	}
</script>

<style lang="scss">
    .array {
        .separator {
            width: 100%;
            height: 1px;
            background-color: rgba($theme-orange, 0.2);
            margin: 12px 0;
        }
        .item {
            .index {
                display: inline-block;
                vertical-align: top;
            }
        }
    }
</style>