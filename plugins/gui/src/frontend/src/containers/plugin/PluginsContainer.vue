<template>
    <scrollable-page title="plugins" class="plugins">
        <scrollable-table :data="plugin.pluginList.data" :fields="plugin.fields" :clickOne="navigatePluginView"
                          :actions="[ { handler: executeQuickView, triggerFont: 'icon-eye' } ]"></scrollable-table>
        <info-dialog :open="infoDialogOpen" title="Plugin Quick View" @close="infoDialogOpen = false">
            <div class="info-dialog-content-title w-100 text-center mt-4">
                <img v-if="plugin.pluginDetails.data['unique_plugin_name']" class="data-logo d-inline-block"
                     :src="`/src/assets/images/logos/${plugin.pluginDetails.data['unique_plugin_name']}.png`">
                <div class="d-inline-block">{{ plugin.pluginDetails.data.name }}</div>
            </div>
            <div v-if="plugin.pluginDetails.data.on" class="text-capitalize w-100 text-center mt-4">
                <i class="icon-play-circle"></i>
                <div class="text-uppercase">running</div>
            </div>
            <div class="w-100 text-center mt-4" v-else>
                <i class="icon-pause-circle"></i>
                <div class="text-uppercase">paused</div>
            </div>
            <a @click="navigatePluginView(plugin.pluginDetails.data.name)" class="btn">Configure</a>
        </info-dialog>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import ScrollableTable from '../../components/ScrollableTable.vue'
    import InfoDialog from '../../components/InfoDialog.vue'

	import { mapState, mapGetters, mapActions } from 'vuex'

    export default {
        name: 'plugins-container',
        components: { ScrollablePage, ScrollableTable, InfoDialog },
        computed: {
            ...mapState([ 'plugin' ])
        },
        data() {
			return {
			    infoDialogOpen: false
            }
		},
        methods: {
        	navigatePluginView(pluginId) {
				this.$router.push({path: `plugin/${pluginId}`});
            },
        	executeQuickView(event, pluginId) {
        		event.preventDefault()
                event.stopPropagation()
				event.target.parentElement.parentElement.parentElement.classList.add('active')
				this.infoDialogOpen = true
            },
        	closeQuickView() {
        		if (this.infoDialogOpen) {
				    this.$el.querySelector(".table-row.active").classList.remove("active")
                }
				this.infoDialogOpen = false
            }
        }
    }
</script>


<style lang="scss">
</style>