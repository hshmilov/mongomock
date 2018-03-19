<template>
    <x-page title="adapters" class="adapters">
        <scrollable-table :data="adapter.adapterList.data" :fields="adapter.adapterFields" @click-row="configAdapter"/>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
    import Card from '../../components/Card.vue'
	import ScrollableTable from '../../components/tables/ScrollableTable.vue'
	import SearchInput from '../../components/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ADAPTERS, FETCH_ADAPTER_SERVERS } from '../../store/modules/adapter'

    export default {
        name: 'adapters-container',
        components: { xPage, Card, ScrollableTable, SearchInput },
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
        	configAdapter(adapter) {
            	/*
            	    Fetch adapter requested to be configured asynchronously, before navigating to the
            	    configuration page, so it will return meanwhile
            	 */
            	this.fetchAdapter(adapter['id'])
                this.$router.push({path: `adapter/${adapter['id']}`})
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