<template>
    <x-page title="alerts">
        <x-data-table module="alert" title="Alerts" @click-row="configAlert" id-field="uuid" v-model="selected">
            <template slot="actions">
                <div v-if="selected && selected.length" @click="removeAlerts" class="link">Remove</div>
                <div @click="createAlert" class="link">+ New Alert</div>
            </template>
        </x-data-table>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataTable from '../../components/tables/DataTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS, SET_ALERT, ARCHIVE_ALERTS } from '../../store/modules/alert'

    export default {
        name: 'alert-container',
        components: { xPage, xDataTable },
		computed: {
            ...mapState(['alert'])
		},
        data() {
        	return {
                selected: []
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT }),
			...mapActions({ fetchAlerts: FETCH_ALERTS, archiveAlerts: ARCHIVE_ALERTS }),
            executeFilter(filterData) {
				/*
				    Upon submission of the filter form, updating the controls of the filter that is passed as props to the
				    paginated table, and so it is re-rendered after fetching the controls with consideration to the new filter
				 */
                this.alertFilter = filterData
            },
            configAlert(alertId) {
				/*
                    Fetch the requested alert configuration and navigate to configuration page with the id, to load it
				 */
				if (!alertId) { return }
                this.setAlert(alertId)
				this.$router.push({path: `alert/${alertId}`})
            },
            createAlert() {
				this.setAlert('new')
				this.$router.push({path: '/alert/new'});
            },
            removeAlerts() {
            	this.archiveAlerts(this.selected)
            }
        }
    }
</script>


<style lang="scss">

</style>