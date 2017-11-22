<template>
    <table class="dynamic-table">
        <thead>
            <tr class="table-row">
                <th class="table-head"></th>
                <th class="table-head" v-for="field in fields">{{ field.name }}</th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="record in data" class="table-row" @click="$emit('select', record['id'])">
                <td>
                    <checkbox class="mr-2"></checkbox>
                </td>
                <generic-table-cell class="table-data" v-for="field in fields" :key="field.path"
                                    :value="record[field.path]" :type="field.type"></generic-table-cell>
            </tr>
            <tr class="table-row" @click="$emit('select', 'new')">
                <td>
                    <checkbox class="mr-2"></checkbox>
                </td>
                <td class="table-data table-btn" :colspan="fields.length">{{ addNewDataLabel }}</td>
            </tr>
        </tbody>
    </table>
</template>

<script>
    import Checkbox from './Checkbox.vue'
    import GenericTableCell from './GenericTableCell.vue'

	export default {
		name: 'dynamic-table',
        components: { Checkbox, GenericTableCell },
        props: ['data', 'fields', 'addNewDataLabel', 'value']
	}
</script>

<style lang="scss">
    @import '../scss/config.scss';

    .dynamic-table {
        border-collapse: separate;
        border-spacing: 0 4px;
        .table-row {
            .table-head {
                font-size: 12px;
                padding: 2px 16px;
            }
            .table-data {
                font-size: 14px;
                padding: 2px 16px;
                border-top: 1px solid $border-color;
                border-bottom: 1px solid $border-color;
                .status-icon {
                    font-size: 16px;
                }
                &:nth-child(2) {
                    padding-left: 2px;
                    border-bottom-left-radius: 4px;
                    border-top-left-radius: 4px;
                    border-left: 1px solid $border-color;
                }
                &:last-of-type {
                    border-bottom-right-radius: 4px;
                    border-top-right-radius: 4px;
                    border-right: 1px solid $border-color;
                }
                &.table-btn {
                    color: $color-disabled;
                }
            }
            &:hover, &.active {
                .table-data {
                    background-color: $background-color-hover;
                    cursor: pointer;
                }
            }
        }
    }
</style>