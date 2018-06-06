<template>
    <div class="x-table-actionable">
        <div class="x-table-header">
            <div class="x-title">
                <div>{{ title }}</div>
                <div v-if="count !== undefined" class="count">({{ count }})</div>
            </div>
            <div class="error">{{error}}</div>
            <div class="x-actions"><slot name="actions"/></div>
        </div>
        <div class="x-table-container" :tabindex="-1" ref="greatTable">
            <div class="v-spinner-bg" v-if="loading"></div>
            <pulse-loader :loading="loading" color="#FF7D46" />
            <slot name="table" />
        </div>
    </div>
</template>

<script>
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

	export default {
		name: 'x-actionable-table',
        components: { PulseLoader },
		props: {
			title: { required: true }, loading: { default: false }, count: { }, error: {}
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
        .x-table-header {
            display: flex;
            padding: 8px;
            line-height: 24px;
            background: $grey-1;
            .x-title {
                display: flex;
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
            max-height: calc(100% - 40px);
            position: relative;
        }
    }
</style>