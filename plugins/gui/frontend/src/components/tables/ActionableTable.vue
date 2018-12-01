<template>
    <div class="x-table-actionable">
        <div class="v-spinner-bg" v-if="loading"></div>
        <pulse-loader :loading="loading" color="#FF7D46" />
        <div class="x-table-header">
            <div class="x-title" v-if="title">
                <div class="title">{{ title }}</div>
                <div v-if="count !== undefined" class="title count">({{ count }})</div>
                <slot name="state" />
            </div>
            <div v-else>
                <x-search-input v-model="searchValue" @input="$emit('search', $event)" placeholder="Search Notes..." />
            </div>
            <div class="error">{{error}}</div>
            <div class="x-actions"><slot name="actions" /></div>
        </div>
        <div class="x-table-container" :tabindex="-1" ref="greatTable">
            <slot name="table" />
        </div>
    </div>
</template>

<script>
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
    import xSearchInput from '../inputs/SearchInput.vue'

	export default {
		name: 'x-actionable-table',
        components: { PulseLoader, xSearchInput },
		props: {
			title: { }, loading: { default: false }, count: { }, error: {}
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
    .x-table-actionable {
        height: calc(100% - 30px);
        background: $theme-white;
        position: relative;
        .x-table-header {
            display: flex;
            padding: 8px 0;
            line-height: 24px;
            background: $grey-0;
            .x-title {
                display: flex;
                line-height: 30px;
                .title {
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
            }
            .x-actions {
                display: grid;
                grid-auto-flow: column;
                grid-gap: 8px;
            }
        }
        .x-table-container {
            overflow: auto;
            max-height: calc(100% - 48px);
        }
    }
</style>