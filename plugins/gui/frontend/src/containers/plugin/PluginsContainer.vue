<template>
    <x-page title="plugins" class="plugins">
        <scrollable-table :data="plugin.pluginList.data" :fields="plugin.fields" :actions="actions"/>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
	import ScrollableTable from '../../components/tables/ScrollableTable.vue'

	import { mapState, mapActions } from 'vuex'
	import { FETCH_PLUGINS, FETCH_PLUGIN, START_PLUGIN, STOP_PLUGIN } from '../../store/modules/plugin'

	export default {
		name: 'plugins-container',
		components: {xPage, ScrollableTable},
		computed: {
			...mapState(['plugin']),
            actions () {
                return [
                    { handler: this.startPlugin, triggerFont: 'icon-play2', conditionField: 'startable' },
                    { handler: this.stopPlugin, triggerFont: 'icon-stop', conditionField: 'stoppable' }
                ]
            }
		},
		data () {
			return {
				infoDialogOpen: false
			}
		},
		methods: {
			...mapActions({fetchPlugins: FETCH_PLUGINS, fetchPlugin: FETCH_PLUGIN,
                startPlugin: START_PLUGIN, stopPlugin: STOP_PLUGIN})
		},
		created () {
			this.fetchPlugins()
		}
	}
</script>


<style lang="scss">
</style>