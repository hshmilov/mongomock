<template>
    <scrollable-page :title="`adapters > ${adapterData.name}`">
        <card title="configure">
            <template slot="cardContent">
                <div class="server-list-container row">
                    <div class="form-group">
                        <!-- Container for list of configured servers - both enabled and disabled -->
                        <div class="form-group-header">
                            <svg-icon name="navigation/device" width="24" height="24" :original="true"></svg-icon>
                            <span class="form-group-title">Add / update Servers</span>
                        </div>
                        <dynamic-table class="ml-4 mt-5" :data="adapterData.servers" :fields="adapter.serverFields"
                                       addNewDataLabel="Add a server" @select="configServer"></dynamic-table>
                    </div>
                </div>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="returnToAdapters">cancel</a>
                        <a class="btn" @click="saveAdapter">save</a>
                    </div>
                </div>
                <modal v-if="serverModal.serverData && serverModal.serverData.id && serverModal.open"
                       class="config-server" @close="toggleServerModal" approveText="save" @confirm="saveServer">
                    <div slot="body">
                        <!-- Container for configuration of a single selected \ added server -->
                        <status-icon-logo-text :logoValue="adapterData['plugin_name']"
                                               :textValue="serverModal.serverData['name']"></status-icon-logo-text>
                        <div class="mt-4 ml-5">
                            <div>Basic System Credentials</div>
                            <generic-form :schema="adapterData.schema" v-model="serverModal.serverData"></generic-form>
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
	import { FETCH_ADAPTER, UPDATE_ADAPTER, UPDATE_ADAPTER_SERVER } from '../../store/modules/adapter'

	export default {
		name: 'adapter-config-container',
        components: { Modal, StatusIconLogoText, GenericForm, ScrollablePage, Card, DynamicTable },
        computed: {
            ...mapState([ 'adapter' ]),
            adapterData() {
            	return this.adapter.currentAdapter.data
            }
        },
        data() {
			return {
				selectedServer: -1,
				serverModal: {
					open: false,
				    serverData: {}
                }
			}
        },
        methods: {
            ...mapActions({
                fetchAdapter: FETCH_ADAPTER,
                updateAdapter: UPDATE_ADAPTER,
                updateAdapterServer: UPDATE_ADAPTER_SERVER
            }),
			returnToAdapters() {
				this.$router.push({name: 'Adapters'})
            },
            saveAdapter() {
				/* Validation */

				/* Save and return to adapters page */
				this.updateAdapter(this.adapterData)
				this.returnToAdapters()
            },
            configServer(serverId) {
            	if (serverId === 'new') {
            		this.selectedServer = this.adapterData.servers.length
					this.serverModal.serverData = { id: serverId }
				} else {
					this.adapterData.servers.forEach((server, index) => {
						if (server.id === serverId) {
							this.selectedServer = index
							this.serverModal.serverData = server
						}
                    })
                }
                this.toggleServerModal()
            },
            saveServer() {
                this.updateAdapterServer({ adapterId: this.adapterData.id, serverData: this.serverModal.serverData })
            	this.toggleServerModal()
            },
            toggleServerModal() {
            	this.serverModal.open = !this.serverModal.open
            }
        },
        created() {
			/*
                If no adapter mapped data source, or has wrong id for current adapter selection,
                try and fetch it (happens after refresh) and update local adapter
             */
			if (!this.adapterData || !this.adapterData.id || (this.$route.params.id !== this.adapterData.id)) {
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