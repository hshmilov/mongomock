<template>
    <scrollable-page :title="`adapters > ${adapterData.name}`" class="">
        <card title="configure">
            <template slot="cardContent">
                <div class="row">
                    <div class="form-group">
                        <div class="form-group-header">
                            <svg-icon name="navigation/device" width="24" height="24" :original="true"></svg-icon>
                            <span class="form-group-title">Add / update Servers</span>
                        </div>
                    </div>
                </div>
                <div>
                    <!-- Container for list of configured servers - both enabled and disabled -->
                    <dynamic-table :data="adapterData.servers" :fields="adapterData.fields"></dynamic-table>
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
				this.returnToAdapters()
            },
            addServer() {

            }
        },
        created() {

        }
	}
</script>

<style lang="scss">

</style>