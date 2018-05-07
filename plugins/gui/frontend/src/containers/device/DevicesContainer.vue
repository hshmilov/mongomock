<template>
    <x-page title="devices">
        <x-data-query module="device" />
        <x-data-table module="device" id-field="internal_axon_id"
                      v-model="selectedDevices" @click-row="configDevice" title="Devices">
            <template slot="actions">
                <!-- Available actions for performing on currently selected group of devices --->
                <devices-actions-container v-show="selectedDevices && selectedDevices.length" :devices="selectedDevices" />
                <x-data-view-menu module="device" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu module="device" class="link" />
                <div class="link" @click="exportCSV">Export csv</div>
            </template>
        </x-data-table>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import DevicesActionsContainer from './DevicesActionsContainer.vue'
	import xDataQuery from '../../components/data/DataQuery.vue'
    import xDataFieldMenu from '../../components/data/DataFieldMenu.vue'
    import xDataViewMenu from '../../components/data/DataViewMenu.vue'
    import xDataTable from '../../components/tables/DataTable.vue'


	import { mapActions } from 'vuex'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'devices-container',
		components: {
			xPage, xDataQuery, xDataTable, DevicesActionsContainer, xDataFieldMenu, xDataViewMenu
		},
        data() {
			return {
				selectedDevices: []
            }
        },
		methods: {
			...mapActions({
                fetchContentCSV: FETCH_DATA_CONTENT_CSV
			}),
			configDevice (deviceId) {
				if (this.selectedDevices && this.selectedDevices.length) return

				this.$router.push({path: `devices/${deviceId}`})
			},
            exportCSV() {
				this.fetchContentCSV({ module: 'device' })
            }
		}
	}
</script>


<style lang="scss">
</style>