<template>
    <scrollable-page :title="`adapters > ${adapterData.name}`" class="">
        <card title="configure">
            <template slot="cardContent">
                <div class="row">
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
                <div v-if="currentServer && currentServer.id">
                    <!-- Container for configuration of a single selected \ added server -->
                    <status-icon-logo-text :logoValue="adapterData['plugin_name']" :textValue="currentServer['name']"></status-icon-logo-text>
                    <generic-form :schema="adapterData.schema" v-model="currentServer"></generic-form>
                </div>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="returnToAdapters">cancel</a>
                        <a class="btn" @click="saveAdapter">save</a>
                    </div>
                </div>
            </template>
        </card>
    </scrollable-page>
</template>

<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import DynamicTable from '../../components/DynamicTable.vue'
	import GenericForm from '../../components/GenericForm.vue'
	import '../../components/icons/navigation'

	import { mapState, mapGetters, mapActions } from 'vuex'
	import { FETCH_ADAPTER, UPDATE_ADAPTER } from '../../store/modules/adapter'
	import StatusIconLogoText from '../../components/StatusIconLogoText.vue'

	export default {
		name: 'adapter-config-container',
        components: {
			StatusIconLogoText,
			GenericForm, ScrollablePage, Card, DynamicTable },
        computed: {
            ...mapState([ 'adapter' ]),
            adapterData() {
            	return this.adapter.currentAdapter.data
            }
        },
        data() {
			return {
				currentServer: {}
            }
        },
        methods: {
            ...mapActions({ fetchAdapter: FETCH_ADAPTER, updateAdapter: UPDATE_ADAPTER }),
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
					this.currentServer.id = serverId
				} else {
					this.adapterData.servers.forEach((server) => {
						if (server.id === serverId) {
							this.currentServer = server
						}
                    })
                }
                console.log(serverId)
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

</style>