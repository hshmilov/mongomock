<template>
    <scrollable-page :title="`adapters > ${adapterName}`">
        <card title="configure">
            <template slot="cardContent">
                <div class="server-list-container row">
                    <div class="form-group">
                        <!-- Container for list of configured servers - both enabled and disabled -->
                        <div class="form-group-header">
                            <svg-icon name="navigation/device" width="24" height="24" :original="true"></svg-icon>
                            <span class="form-group-title">Add / update Servers</span>
                        </div>
                        <dynamic-table v-if="schemaFields" class="ml-4 mt-5" :data="adapterData.clients"
                                       :fields="schemaFields"
                                       addNewDataLabel="Add a server" @select="configServer" @delete="deleteServer">
                        </dynamic-table>
                    </div>
                </div>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="returnToAdapters">cancel</a>
                        <a class="btn" @click="saveAdapter">save</a>
                    </div>
                </div>
                <modal v-if="serverModal.serverData && serverModal.uuid && serverModal.open"
                       class="config-server" @close="toggleServerModal" approveText="save" @confirm="saveServer">
                    <div slot="body">
                        <!-- Container for configuration of a single selected / added server -->
                        <status-icon-logo-text :logoValue="adapterPluginName"
                                               :textValue="serverModal.serverData['name']"></status-icon-logo-text>
                        <div class="mt-4 ml-5">
                            <div>Basic System Credentials</div>
                            <generic-form :schema="schemaFields" v-model="serverModal.serverData"></generic-form>
                        </div>
                    </div>
                </modal>
            </template>
        </card>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
	import Card from '../../components/Card.vue'
	import DynamicTable from '../../components/DynamicTable.vue'
	import GenericForm from '../../components/GenericForm.vue'
	import StatusIconLogoText from '../../components/StatusIconLogoText.vue'
	import Modal from '../../components/Modal.vue'
	import '../../components/icons/navigation'

	import { mapState, mapGetters, mapActions } from 'vuex'
	import {
		FETCH_ADAPTER_SERVERS, SAVE_ADAPTER_SERVER, ARCHIVE_SERVER, adapterStaticData
	} from '../../store/modules/adapter'

	export default {
		name: 'adapter-config-container',
		components: {Modal, StatusIconLogoText, GenericForm, ScrollablePage, Card, DynamicTable},
		computed: {
			...mapState(['adapter']),
			adapterUniquePluginName () {
				return this.$route.params.id
			},
			adapterPluginName () {
				return this.adapterUniquePluginName.match(/(.*_adapter)_\d*/)[1]
			},
			adapterName () {
				return adapterStaticData[this.adapterPluginName].name
			},
			adapterData () {
				return this.adapter.currentAdapter.data
			},
			schemaFields () {
				let fields = []
				if (!this.adapterData.schema) { return }
				Object.keys(this.adapterData.schema.properties).forEach((fieldKey) => {
					let field = {
						path: fieldKey, name: fieldKey, control: this.adapterData.schema.properties[fieldKey].type,
						required: this.adapterData.schema.required.indexOf(fieldKey) > -1
					}
					if (field.control === 'password') {
						field.hidden = true
					}
					fields.push(field)
				})
				return fields
			}
		},
		data () {
			return {
				selectedServer: -1,
				serverModal: {
					open: false,
					serverData: {},
                    uuid: null,
				}
			}
		},
		methods: {
			...mapActions({
				fetchAdapter: FETCH_ADAPTER_SERVERS,
				updateAdapterServer: SAVE_ADAPTER_SERVER,
                archiveServer: ARCHIVE_SERVER
			}),
			returnToAdapters () {
				this.$router.push({name: 'Adapters'})
			},
			saveAdapter () {
				/* Validation */

				/* Save and return to adapters page */
//				this.updateAdapter(this.adapterData)
				this.returnToAdapters()
			},
			configServer (serverId) {
				if (serverId === 'new') {
					this.selectedServer = this.adapterData.clients.length
					this.serverModal.serverData = {}
					this.serverModal.uuid = serverId
				} else {
					this.adapterData.clients.forEach((server, index) => {
						if (server.uuid === serverId) {
							this.selectedServer = index
							this.serverModal.serverData = {}
							Object.keys(server).filter((key) => {
								return key !== 'uuid'
                            }).forEach((filteredKey) => {
								this.serverModal.serverData[filteredKey] = server[filteredKey]
                            })
                            this.serverModal.uuid = server.uuid
						}
					})
				}
				this.toggleServerModal()
			},
			deleteServer (serverId) {
                this.archiveServer({
                    adapterId: this.adapterUniquePluginName,
                    serverId: serverId
                })
			},
			saveServer () {
				this.updateAdapterServer({
					adapterId: this.adapterUniquePluginName,
					serverData: this.serverModal.serverData,
                    uuid: this.serverModal.uuid
				})
				this.toggleServerModal()
			},
			toggleServerModal () {
				this.serverModal.open = !this.serverModal.open
			}
		},
		created () {
			/*
                If no adapter mapped data source, or has wrong id for current adapter selection,
                try and fetch it (happens after refresh) and update local adapter
             */
			if (!this.adapterData || !this.adapterData.schema) {
				this.fetchAdapter(this.$route.params.id)
			}
		}
	}
</script>

<style lang="scss">
    .config-server {
        .form-group {
            padding-left: 12px;
        }
    }
</style>