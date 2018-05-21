<template>
    <div>
        <div class="x-table-header">
            <div class="x-title">{{ title }} ({{count}})</div>
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
		name: 'actionable-table',
        components: { PulseLoader },
		props: {
			title: { required: true }, loading: { default: false }, count: { default: 0 }
		},
        mounted() {
			this.$refs.greatTable.focus()
        }
	}
</script>

<style lang="scss">
    .x-table-header {
        display: flex;
        padding: 8px;
        line-height: 24px;
        .x-title {
            flex: 1 0 auto;
        }
        .x-actions {
            display: grid;
            grid-auto-flow: column;
            grid-gap: 8px;
        }
    }
    .x-table-container {
        overflow: auto;
        max-height: calc(100% - 80px);
        position: relative;
        .item > div {
            display: inline;
        }
        .array {
            height: 24px;
        }
    }
</style>