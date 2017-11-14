<template>
    <scrollable-page title="queries history" class="query">
        <card :title="`queries (${query.savedQueries.data.length})`">
            <paginated-table slot="cardContent" :fetching="query.savedQueries.fetching"
                             :data="query.savedQueries.data" :error="query.savedQueries.error"
                             :fields="query.fields" :fetchData="fetchQueries"></paginated-table>
        </card>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../../components/ScrollablePage.vue'
    import Card from '../../../components/Card.vue'
    import ActionBar from '../../../components/ActionBar.vue'
    import GenericForm from '../../../components/GenericForm.vue'
    import PaginatedTable from '../../../components/PaginatedTable.vue'
    import SearchInput from '../../../components/SearchInput.vue'

    import { mapState, mapGetters, mapActions } from 'vuex'
    import { FETCH_QUERIES } from '../../../store/modules/query'

    export default {
        name: 'queries-container',
        components: {
            SearchInput,
            ScrollablePage, Card, ActionBar, GenericForm, PaginatedTable},
        computed: {
            ...mapState(['query'])
        },
        data() {
            return {
                querySearchValue: ''
            }
        },
        methods: {
          ...mapActions({
              fetchQueries: FETCH_QUERIES
          })
        }
    }
</script>


<style lang="scss">
    .query {
        .form-label {
            font-size: 80%;
        }
        .search-input {
            width: 40%;
            margin-top: 12px;
            margin-left: 8px;
        }
    }
</style>