<template>
    <x-page title="devices">
        <x-data-query :module="module" />
        <x-data-table :module="module" id-field="internal_axon_id" v-model="selectedDevices" title="Devices"
                      @click-row="configDevice" @data="updateDeviceState" ref="table">
            <template slot="actions">
                <!-- Available actions for performing on currently selected group of devices --->
                <devices-actions-container v-show="anySelected" :devices="selectedDevices" @done="updateDevices" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu :module="module" />
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
    import xDataTable from '../../components/tables/DataTable.vue'


	import { mapState, mapActions, mapMutations } from 'vuex'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'
	import { CHANGE_TOUR_STATE, UPDATE_TOUR_STATE } from '../../store/modules/onboarding'

	export default {
		name: 'devices-container',
		components: {
			xPage, xDataQuery, xDataTable, DevicesActionsContainer, xDataFieldMenu
		},
        computed: {
            ...mapState({
				tourDevices(state) {
					return state.onboarding.tourStates.queues.devices
				}
            }),
			module() {
				return 'devices'
            },
            anySelected() {
				return (this.selectedDevices && this.selectedDevices.length)
            }
        },
        data() {
			return {
				selectedDevices: []
            }
        },
		methods: {
			...mapActions({ fetchContentCSV: FETCH_DATA_CONTENT_CSV }),
            ...mapMutations({ changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE }),
			configDevice (deviceId) {
				if (this.anySelected) return

				this.$router.push({path: `${this.module}/${deviceId}`})
			},
            exportCSV() {
				this.fetchContentCSV({ module: this.module })
            },
            updateDeviceState(deviceId) {
				if (!this.tourDevices || !this.tourDevices.length) return
				if (this.tourDevices[0] === 'bestDevice') {
				    this.changeState({ name: 'bestDevice', id: deviceId })
                } else {
			        this.changeState({name: this.tourDevices[0]})
                }
            },
            updateDevices() {
				this.$refs.table.fetchContentPages()
                this.selectedDevices = []
			}
		}
	}
</script>


<style lang="scss">
</style>