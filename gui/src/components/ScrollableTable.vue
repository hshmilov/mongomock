<template>
    <div>
        <table class="table scrollable-table">
            <thead>
            <tr>
                <th v-for="field in fields" class="table-head">{{ field.name }}</th>
                <th class="table-head" v-if="actions !== undefined"></th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="record in data" class="table-row">
                <td v-for="field, index in fields" class="table-row-data">
                    <template v-if="field.type === 'status-icon-logo-text'">
                        <status-icon-logo-text :textValue="record[field.path]" :logoValue="record['plugin_name']"
                                               :statusIconValue="record['status']"></status-icon-logo-text>
                    </template>
                    <template v-else>
                        {{ record[field.path] }}
                    </template>
                </td>
                <td class="table-row-data table-row-actions" v-if="actions !== undefined">
                    <a v-for="action in actions" @click="action.execute($event, record['id'])">
                        <i :class="action.icon"></i>
                    </a>
                </td>
            </tr>
            </tbody>
        </table>
        <div v-if="error">{{ error }}</div>
    </div>
</template>

<script>
	import StatusIconLogoText from './StatusIconLogoText.vue'

	export default {
		name: 'scrollable-table',
		components: { StatusIconLogoText },
		props: ['data', 'fetching', 'error', 'fields', 'actions'],
		methods: {}
	}
</script>

<style lang="scss">
    @import '../scss/config';

    .scrollable-table {
        border-collapse: separate;
        border-spacing: 0px 8px;
        margin-top: -8px;
        margin-bottom: 0;
        .table-head {
            font-size: 80%;
            font-weight: 300;
            background-color: $background-color-title;
            border: 1px solid $border-color;
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
        .table-row {
            background-color: $background-color-light;
            box-shadow: 0px 4px 4px rgba(0, 0, 0, 0.08);
            &.clickable {
                cursor: pointer;
            }
            &:hover, &.active {
                background-color: $background-color-hover;
                .table-row-actions a {
                    visibility: visible;
                }
            }
        }
        .table-row-data {
            vertical-align: middle;
            padding: 20px;
            position: relative;
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
            .table-row-actions {
                text-align: center;
                a {
                    visibility: hidden;
                    &:hover {
                        color: $color-theme;
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