<template>
    <div class="array">
        <label v-if="schema.title" :title="schema.description || ''" class="label">{{schema.title}}</label>
        <div v-for="item in schemaItems" class="item">
            <x-object :schema="item">
                <component :is="`x-${item.type}-edit`" :schema="item" v-model="data[item.name]"
                           @input="$emit('input', data)" :validator="validator"></component>
            </x-object>
        </div>
    </div>
</template>

<script>
	import xObject from '../Object.vue'
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
			xObject,
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