<template>
    <div class="array">
        <label v-if="schema.title" :title="schema.description || ''" class="label">{{schema.title}}</label>
        <div v-for="item in schemaItems" class="item">
            <x-type-wrap :name="item.name" :type="item.type" :title="item.title" :description="item.description">
                <component :is="`x-${item.type}-edit`" :schema="item" v-model="data[item.name]"
                           @input="$emit('input', data)" :validator="validator"></component>
            </x-type-wrap>
        </div>
    </div>
</template>

<script>
	import xTypeWrap from './TypeWrap.vue'
	import xStringEdit from '../string/StringEdit.vue'
	import xNumberEdit from '../numerical/NumberEdit.vue'
	import xIntegerEdit from '../numerical/IntegerEdit.vue'
	import xBoolEdit from '../boolean/BooleanEdit.vue'
	import xFileEdit from './FileEdit.vue'

    import ArrayMixin from './array'

	export default {
		name: 'x-array-edit',
        mixins: [ArrayMixin],
		components: {
			xTypeWrap,
			xStringEdit,
			xNumberEdit,
			xIntegerEdit,
			xBoolEdit,
			xFileEdit
		},
		props: ['validator']
	}
</script>

<style lang="scss">

    .item {
        margin-bottom: .5rem;
        .index {
            display: inline-block;
            vertical-align: top;
        }
    }
</style>