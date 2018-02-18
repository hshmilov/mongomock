<template>
    <div class="schema-list">
        <x-array-view :value="data" :schema="schema" :limit="limit"></x-array-view>
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
        props: {data: {required: true}, schema: {required: true}, limit: {default: false}}
	}
</script>

<style lang="scss">
    .schema-list {
        .label, .index {
            font-weight: 500;
        }
    }
</style>