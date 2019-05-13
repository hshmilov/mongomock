<template>
    <div class="x-table-wrapper">
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46"/>
        <div class="table-header">
            <div class="title" v-if="title">
                <div class="text">{{ title }}</div>
                <div v-if="count !== undefined" class="title count">({{ count }})</div>
                <slot name="state"/>
            </div>
            <div class="error">{{error}}</div>
            <div class="actions">
                <slot name="actions"/>
            </div>
        </div>
        <div class="table-container" :tabindex="-1" ref="greatTable">
            <div class="table-title"></div>
            <div class="table-data">
                <slot name="table"/>
            </div>

        </div>
    </div>
</template>

<script>
    import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
    import xSearchInput from '../../neurons/inputs/SearchInput.vue'

    export default {
        name: 'x-table-wrapper',
        components: {PulseLoader, xSearchInput},
        props: {
            title: {}, loading: {default: false}, count: {}, error: {}
        },
        data() {
            return {
                searchValue: ''
            }
        },
        mounted() {
            this.$refs.greatTable.focus()
        }
    }
</script>

<style lang="scss">
    .x-table-wrapper {
        height: calc(100% - 30px);
        background: $theme-white;
        position: relative;

        .table-header {
            display: flex;
            padding: 8px 0;
            line-height: 24px;
            background: $grey-0;
            align-items: flex-end;

            .title {
                display: flex;
                line-height: 30px;

                .text {
                    font-weight: 400;
                }

                .count {
                    margin-left: 8px;
                }
            }

            .error {
                flex: 1 0 auto;
                color: $indicator-error;
                display: inline-block;
                margin-left: 24px;
                font-size: 12px;
                white-space: pre;
            }

            .actions {
                display: grid;
                grid-auto-flow: column;
                grid-template-columns: max-content;
                grid-gap: 8px;
            }
        }

        .table-container {
            position: relative;
            height: calc(100% - 48px);
            padding-top: 30px;
            overflow: auto;

            .table-title {
                height: 30px;
                position: absolute;
                top: 0;
                right: 0;
                left: 0;
            }
            .table-data {
                height: 100%;
                overflow: auto;
                width: max-content;
                min-width: 100%;
                border-top: 2px dashed $grey-2;
            }
        }
    }
</style>