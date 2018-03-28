<template>
    <div class="scrollable-table">
        <table class="table">
            <thead>
            <tr class="table-header">
                <th v-for="field in fields"  v-if="!field.hidden" class="table-head">{{ field.name }}</th>
                <th class="table-head" v-if="actions !== undefined"></th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="record in data" class="table-row" @click="$emit('click-row', record)">
                <generic-table-cell class="table-row-data" v-for="field in fields" v-if="!field.hidden" :key="field.path"
                                    :value="record[field.path]" :type="field.type" :wide="true"/>
                <td class="table-row-data table-row-actions" v-if="actions !== undefined">
                    <template v-for="action in actions">
                        <a  class="table-row-action" @click.stop="action.handler(record['id'])"
                            v-if="!action.conditionField || record[action.conditionField]">
                            <i :class="action.triggerFont" v-if="action.triggerFont"></i>
                            <svg-icon :name="action.triggerIcon" height="24" width="24" :original="true" v-else/>
                        </a>
                    </template>
                </td>
            </tr>
            </tbody>
        </table>
        <div v-if="error">{{ error }}</div>
    </div>
</template>

<script>
	import StatusIconLogoText from '../StatusIconLogoText.vue'
	import GenericTableCell from '../tables/GenericTableCell.vue'
	import '../icons'

	export default {
		name: 'scrollable-table',
		components: {
			GenericTableCell,
			StatusIconLogoText },
		props: ['data', 'fetching', 'error', 'fields', 'actions'],
		methods: {}
	}
</script>

<style lang="scss">
    .scrollable-table {
        height: calc(100vh - 170px);
        overflow: auto;
        .table {
            border-collapse: separate;
            border-spacing: 0px 8px;
            margin-top: -8px;
            margin-bottom: 0;
            font-size: 14px;
            .table-header {
                border: 0;
                .table-head {
                    background-color: transparent;
                    font-size: 80%;
                    font-weight: 300;
                    border: 0;
                    padding: 4px 12px;
                    &:first-of-type {
                        border-bottom-left-radius: 4px;
                        border-top-left-radius: 4px;
                    }
                    &:last-of-type {
                        border-bottom-right-radius: 4px;
                        border-top-right-radius: 4px;
                    }
                    &:not(:first-of-type) {
                        border-left: 0;
                    }
                    &:not(:last-of-type) {
                        border-right: 0;
                    }
                }
            }
            .table-row {
                background-color: $background-color-light;
                &.clickable {
                    cursor: pointer;
                }
                &:hover, &.active {
                    background-color: $background-color-hover;
                    .table-row-data {
                        border-left-color: $background-color-light;
                    }
                    .table-row-actions .table-row-action {
                        visibility: visible;
                        .svg-stroke {  stroke: $color-text-title;  }
                        .svg-fill {  fill: $color-text-title;  }
                        &:hover {
                            .svg-stroke {  stroke: $color-theme-light;  }
                            .svg-fill {  fill: $color-theme-light;  }
                        }
                    }
                }
            }
            .table-row-data {
                vertical-align: middle;
                padding: 20px;
                position: relative;
                max-width: 240px;
                &:first-of-type {
                    border-bottom-left-radius: 4px;
                    border-top-left-radius: 4px;
                }
                &:last-of-type {
                    border-bottom-right-radius: 4px;
                    border-top-right-radius: 4px;
                }
                &:not(:first-of-type) {
                    border-left: 2px solid $background-color;
                }
            }
            .table-row-actions {
                text-align: right;
                .table-row-action {
                    visibility: hidden;
                    padding-right: 20px;
                    &:hover {
                        color: $color-theme-light;
                        .svg-stroke {  stroke: $color-theme-light;  }
                        .svg-fill {  fill: $color-theme-light;  }
                    }
                    i {
                        vertical-align: middle;
                        font-size: 120%;
                    }
                }
            }
        }
    }
</style>