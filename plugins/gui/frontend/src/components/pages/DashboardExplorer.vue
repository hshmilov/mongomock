<template>
    <x-page :breadcrumbs="[
    	{ title: 'axonius cards', path: { name: 'Dashboard'}},
    	{ title: 'Search' }
    ]">
        <x-search-insights/>
        <div class="explorer-results">
            <x-table v-for="entity in entities" :key="entity['internal_axon_id']" id-field="internal_axon_id"
                     :module="entity.name" section="explorer" @click-row="configEntity($event, entity.name)">
                <template slot="actions">
                    <button class="x-btn link" @click="viewEntities(entity.name)">View in {{ entity.title }}</button>
                </template>
            </x-table>
        </div>
    </x-page>

</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xSearchInsights from '../neurons/inputs/SearchInsights.vue'
    import xTable from '../neurons/data/Table.vue'
    import {entities} from '../../constants/entities'

    import {mapState, mapMutations} from 'vuex'
    import {UPDATE_DATA_VIEW} from '../../store/mutations'

    export default {
        name: 'x-dashboard-explorer',
        components: {xPage, xSearchInsights, xTable},
        computed: {
            ...mapState({
                entityFilters(state) {
                    let entityToFilter = {}
                    entities.forEach(entity => {
                        entityToFilter[entity.name] = state['explorer'][entity.name].view.query.filter
                    })
                    return entityToFilter
                }
            }),
            entities() {
                return entities
            }
        },
        methods: {
            ...mapMutations({updateDataView: UPDATE_DATA_VIEW}),
            configEntity(entityId, entityType) {
                this.$router.push({
                    path: `/${entityType}/${entityId}`
                })
            },
            viewEntities(entityType) {
                this.updateDataView({
                    module: entityType, view: {
                        query: {
                            filter: this.entityFilters[entityType]
                        }
                    }
                })
                this.$router.push({
                    path: `/${entityType}`
                })
            }
        }
    }
</script>

<style lang="scss">
    .explorer-results {
        height: calc(100% - 48px);

        .x-data-table {
            height: 50%;
        }
    }
</style>