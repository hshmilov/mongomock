<template>
    <div class="schema-list">
        <div class="actions-bar">
            <div @click="expandAll" class="x-btn link">+ Expand all</div>
            <div @click="collapseAll" class="x-btn link">- Collapse all</div>
        </div>
        <x-array-view :value="data" :schema="schema" ref="arrayView" />
    </div>
</template>

<script>
    import xArrayView from '../controls/array/ArrayView.vue'

    /*
        Dynamically built list of nested data, structured according to given schema, filled with given value.
        Schema is expected to be of type array (can be tuple). Data is expected to comply to given schema's definition.
        If limit is on, only data included in 'required' will be presented.
     */
	export default {
		name: 'x-schema-list',
        components: { xArrayView },
        props: { data: { required: true }, schema: { required: true } },
        methods: {
			expandAll() {
				this.$refs.arrayView.collapseRecurse(false)
            },
			collapseAll() {
				this.$refs.arrayView.collapseRecurse(true)
			}
        }
	}
</script>

<style lang="scss">
    .schema-list {
        .actions-bar {
            display: flex;
            justify-content: flex-end;
            .x-btn {
                font-size: 12px;
            }
        }
    }
</style>