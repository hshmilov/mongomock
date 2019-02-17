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
            <div v-else>
                <x-search-input v-model="searchValue" @input="$emit('search', $event)" placeholder="Search Notes..."/>
            </div>
            <div class="error">{{error}}</div>
            <div class="actions">
                <slot name="actions"/>
            </div>
        </div>
        <div class="table-container" :tabindex="-1" ref="greatTable">
            <slot name="table"/>
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
            overflow: auto;
            max-height: calc(100% - 48px);
        }
    }
</style>