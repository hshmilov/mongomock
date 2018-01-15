<template>
    <div>
        <label v-if="title" :title="description || ''" class="data-label">{{title}}:</label>
        <template v-if="Array.isArray(items)">
            <div v-for="schema in items" v-if="data[schema.name] && included(schema.name)">
                <object-schema :data="data[schema.name]" :schema="schema"></object-schema>
            </div>
        </template>
        <template v-else-if="items instanceof Object">
            <div v-for="item, index in data">
                <div class="item-index ml-2">{{index+1}}.</div>
                <object-schema :data="item" :schema="items"></object-schema>
            </div>
        </template>
    </div>
</template>

<script>
    import ObjectSchema from './ObjectSchema.vue'

	export default {
		name: 'array',
        props: ['items', 'title', 'description', 'required', 'data'],
        methods: {
			included(fieldName) {
				if (!this.required) {
					return true
                }
                return this.required.includes(fieldName)
            }
        }
	}
</script>

<style lang="scss">
    .item-index {
        display: inline-block;
        vertical-align: top;
    }
</style>