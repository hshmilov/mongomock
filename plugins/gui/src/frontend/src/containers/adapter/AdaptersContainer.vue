<template>
    <scrollable-page title="adapters" class="adapters">
        <card>
            <div slot="cardContent" class="row">
                <div class="form-group col-6 row">
                    <label class="form-label col-3">Search:</label>
                    <search-input class="col-9" v-model="filter.name" placeholder="Enter name..."></search-input>
                </div>
                <div class="form-group col-6 filter-status">
                    <label class="form-label">Show Only</label>
                    <select class="col-6 custom-select">
                        <option value="connected">Connected</option>
                        <option value="not connected">Not Connected</option>
                        <option value="connection failure">Connection Failure</option>
                    </select>
                </div>
            </div>
        </card>
        <scrollable-table :data="adapter.adapterList.data" :fields="adapter.adapterFields" :actions="[
        	{triggerFont: 'icon-pencil2', handler: configAdapter}]"></scrollable-table>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
	import ScrollableTable from '../../components/ScrollableTable.vue'
	import SearchInput from '../../components/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ADAPTERS, FETCH_ADAPTER_SERVERS } from '../../store/modules/adapter'

    export default {
        name: 'adapters-container',
        components: { ScrollablePage, Card, ScrollableTable, SearchInput },
        computed: { ...mapState(['adapter']) },
        data() {
        	return {
        		filter: {
        			name: ''
                }
            }
        },
        methods: {
            ...mapActions({ fetchAdapters: FETCH_ADAPTERS, fetchAdapter: FETCH_ADAPTER_SERVERS }),
        	configAdapter(adapterId) {
            	/*
            	    Fetch adapter requested to be configured asynchronously, before navigating to the
            	    configuration page, so it will return meanwhile
            	 */
            	this.fetchAdapter(adapterId)
                this.$router.push({path: `adapter/${adapterId}`})
            },
            quickViewAdapter(adapterId) {

            }
        },
        created() {
            this.fetchAdapters()
        }
    }
</script>


<style lang="scss">
    .adapters {
        .row {
            .form-group {
                margin-bottom: 0;
                &.filter-status {
                    text-align: right;
                }
            }
            .search-input {
                width: auto;
                .input-group-addon {
                    right: 12px;
                }
            }
        }
    }
</style>