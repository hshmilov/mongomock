<template>
    <div class="x-list">
        <div class="list-actions">
            <x-button @click="expandAll" link>+ Expand all</x-button>
            <x-button @click="collapseAll" link>- Collapse all</x-button>
        </div>
        <x-array-view :value="data" :schema="schema" ref="arrayView"/>
    </div>
</template>

<script>
    import xArrayView from './types/array/ArrayView.vue'
    import xButton from '../../axons/inputs/Button.vue'

    /*
        Dynamically built list of nested data, structured according to given schema, filled with given value.
        Schema is expected to be of type array (can be tuple). Data is expected to comply to given schema's definition.
        If limit is on, only data included in 'required' will be presented.
     */
    export default {
        name: 'x-list',
        components: {xArrayView, xButton},
        props: {data: {required: true}, schema: {required: true}},
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
    .x-list {
        .list-actions {
            display: flex;
            justify-content: flex-end;

            .x-button {
                font-size: 12px;
            }
        }
    }
</style>