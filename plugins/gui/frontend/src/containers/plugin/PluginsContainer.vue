<template>
    <scrollable-page title="plugins" class="plugins">
        <scrollable-table :data="plugin.pluginList.data" :fields="plugin.fields" :actions="actions" @click-row="configPlugin"></scrollable-table>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
	import ScrollableTable from '../../components/tables/ScrollableTable.vue'
	import InfoDialog from '../../components/popover/InfoDialog.vue'

	import { mapState, mapActions } from 'vuex'
	import { FETCH_PLUGINS, FETCH_PLUGIN, START_PLUGIN, STOP_PLUGIN } from '../../store/modules/plugin'

	export default {
		name: 'plugins-container',
		components: {ScrollablePage, ScrollableTable, InfoDialog},
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
                startPlugin: START_PLUGIN, stopPlugin: STOP_PLUGIN}),
			configPlugin (plugin) {
				if (!plugin.configurable) {
					return
                }
				this.fetchPlugin(plugin['id'])
				this.$router.push({path: `plugin/${plugin['id']}`})
			}
		},
		created () {
			this.fetchPlugins()
		}
	}
</script>


<style lang="scss">
</style>