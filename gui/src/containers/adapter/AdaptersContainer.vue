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
                    <select class="col-6">
                        <option value="connected">Connected</option>
                        <option value="not connected">Not Connected</option>
                        <option value="connection failure">Connection Failure</option>
                    </select>
                </div>
            </div>
        </card>
        <scrollable-table :data="adapter.adapterList.data" :fields="adapter.fields" :actions="[
        	{triggerFont: 'icon-pencil2', handler: configAdapter},
        	{triggerFont: 'icon-eye', handler: quickViewAdapter}
        	]"></scrollable-table>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
	import ScrollableTable from '../../components/ScrollableTable.vue'
	import SearchInput from '../../components/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'

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
        	configAdapter(adapterId) {

            },
            quickViewAdapter(adapterId) {

            }
        }
    }
</script>


<style lang="scss">
    .adapters {
        :not(.row) > .row {
            margin-top: 12px;
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