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
                <tr @click="clickOne(record['name'])" v-for="record in data" class="table-row"
                    v-bind:class="{ clickable: (clickOne !== undefined) }">
                    <td v-for="field, index in fields" class="table-row-data">
                        <div v-if="!index"
                             :class="`data-status XXXX data-status-${record['isOn'] ? 'on' : 'off'}`"></div>
                        <img v-if="!index && record['unique_plugin_name']" class="data-logo"
                             :src="`/src/assets/images/logos/${record['unique_plugin_name']}.png`">
                        {{ record[field.path] }}
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
  export default {
    name: 'scrollable-table',
    props: ['data', 'fetching', 'error', 'fields', 'actions', 'clickOne'],
    methods: {

    }
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
            },
            .table-row-data {
                vertical-align: middle;
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
                .data-status {
                    height: 60px;
                    width: 20px;
                    display: inline-block;
                    border-radius: 4px;
                    margin-right: 8px;
                    margin-top: -10px;
                    margin-left: -10px;
                    margin-bottom: -18px;
                    background-color: $background-color-title;
                    &.data-status-on {
                        background-color: $color-success;
                    }
                    &.data-status-off {
                        background-color: $background-color-error;
                    }
                }
                .data-logo {
                    height: 36px;
                    margin-right: 12px;
                    margin-top: -12px;
                }
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