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
                        <dynamic-table class="ml-4 mt-5" :data="adapterData.servers" :fields="adapterData.fields"
                                       addNewDataLabel="Add a server" @select="configServer"></dynamic-table>
                    </div>
                </div>
                <div>
                    <!-- Container for configuration of a single selected \ added server -->

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
    import '../../components/icons/navigation'

	import { mapState, mapGetters, mapActions } from 'vuex'
    import { UPDATE_ADAPTER } from '../../store/modules/adapter'

	export default {
		name: 'adapter-config-container',
        components: { ScrollablePage, Card, DynamicTable },
        computed: {
            ...mapState([ 'adapter' ]),
            adapterData() {
            	return this.adapter.currentAdapter.data
            }
        },
        methods: {
            ...mapActions({ updateAdapter: UPDATE_ADAPTER }),
			returnToAdapters() {
				this.$router.push({name: 'Adapter'})
            },
            saveAdapter() {
				/* Validation */

				/* Save and return to adapters page */
				this.updateAdapter(this.adapterData)
				this.returnToAdapters()
            },
            configServer(serverId) {
                console.log(serverId)
            }
        },
        created() {
			/*
                If no adapter mapped data source, or has wrong id for current adapter selection,
                try and fetch it (happens after refresh) and update local adapter
             */
			if (!this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
				this.fetchAlert(this.$route.params.id)
			}
        }
	}
</script>

<style lang="scss">

</style>