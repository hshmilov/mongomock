<template>
    <x-page title="adapters" class="x-adapters">
        <div class="adapters-search">
            <x-search-input v-model="searchText" placeholder="Search Adapters..."/>
        </div>
        <div class="adapters-table">
            <table class="table">
                <thead>
                <tr class="table-row">
                    <th class="status">&nbsp;</th>
                    <th class="row-data">Name</th>
                    <th class="row-data">Description</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="item in adaptersData" @click="configAdapter(item['id'])" class="table-row">
                    <td class="status">
                        <div class="symbol">
                            <svg-icon :name="`symbol/${item['status']}`" :original="true" height="20px"></svg-icon>
                        </div>
                        <div class="marker" :class="`indicator-bg-${item['status'] || 'void'}`"></div>
                    </td>
                    <td class="row-data" :id="item.id">
                        <x-title :id="item.id" :logo="`adapters/${item.id}`">{{ item.title }}</x-title>
                    </td>
                    <td class="row-data">
                        <div class="content">{{ item.description }}</div>
                    </td>
                </tr>
                </tbody>
            </table>
        </div>
    </x-page>
</template>


<script>
    import xPage from '../axons/layout/Page.vue'
    import xTitle from '../axons/layout/Title.vue'
    import xSearchInput from '../neurons/inputs/SearchInput.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {FETCH_ADAPTERS} from '../../store/modules/adapters'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-adapters',
        components: {xPage, xTitle, xSearchInput},
        computed: {
            ...mapState({
                adaptersData(state) {
                    if (state.adapters.adapterList.data.length > 0) {
                        return state.adapters.adapterList.data.filter(adapter => {
                            return adapter.title.toLowerCase().includes(this.searchText.toLowerCase())
                        })
                    }
                },
                tourAdapters(state) {
                    return state.onboarding.tourStates.queues.adapters
                }
            })
        },
        data() {
            return {
                searchText: ''
            }
        },
        methods: {
            ...mapMutations({changeState: CHANGE_TOUR_STATE}),
            ...mapActions({fetchAdapters: FETCH_ADAPTERS}),
            configAdapter(adapterId) {
                /*
                    Fetch adapters requested to be configured asynchronously, before navigating to the
                    configuration page, so it will return meanwhile
                 */
                this.$router.push({path: `adapters/${adapterId}`})
            }
        },
        created() {
            this.fetchAdapters().then(() => {
                this.changeState({name: this.tourAdapters[0]})
            })
        }
    }
</script>


<style lang="scss">
    .x-adapters {
        .adapters-search {
            margin-bottom: 12px;
        }

        .adapters-table {
            height: calc(100% - 42px);
            overflow: auto;

            .table {
                border-collapse: separate;
                border-spacing: 0 8px;
                font-size: 14px;
                overflow: hidden;

                .table-row {
                    .row-data {
                        background: $theme-white;
                        vertical-align: middle;
                        padding: 12px;
                        position: relative;

                        &:last-child {
                            border-bottom-right-radius: 4px;
                            border-top-right-radius: 4px;
                        }

                        .content {
                            line-height: 1.2em;
                            overflow: hidden;
                            display: -webkit-box;
                            -webkit-line-clamp: 3;
                            -webkit-box-orient: vertical;
                        }
                    }

                    .status {
                        display: flex;
                        box-shadow: none;

                        .symbol {
                            flex: 1 0 auto;
                            text-align: center;
                            line-height: calc(3.6em + 24px);
                            margin: 0 12px;
                        }

                        .marker {
                            width: 10px;
                            height: calc(4px + 3.6em + 24px);
                            margin: -2px -8px;
                            border-bottom-left-radius: 4px;
                            border-top-left-radius: 4px;

                        }
                    }
                }

                thead {
                    overflow: auto;
                    .table-row .row-data:nth-child(2) {
                        border-bottom-left-radius: 4px;
                        border-top-left-radius: 4px;
                    }
                }

                tbody {
                    overflow: auto;
                    .table-row:hover {
                        cursor: pointer;
                        transform: scale(1.02);
                    }
                }
            }

        }
    }
</style>