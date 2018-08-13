<template>
    <x-page title="adapters" class="adapters">
        <div class="adapters-search">
            <x-search v-model="searchText" placeholder="Search Adapters..." />
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
                        <td class="row-data" :id="item.plugin_name">
                            <x-logo-name :name="item.plugin_name"/>
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
	import xPage from '../../components/layout/Page.vue'
    import xLogoName from '../../components/titles/LogoName.vue'
    import xSearch from '../../components/inputs/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ADAPTERS } from '../../store/modules/adapter'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

    export default {
        name: 'adapters-container',
        components: { xPage, xLogoName, xSearch },
        computed: {
            ...mapState({
                adaptersData(state) {
                	return state.adapter.adapterList.data.filter(adapter => {
                		return adapter.title.toLowerCase().includes(this.searchText.toLowerCase())
                    })
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
            ...mapMutations({ changeState: CHANGE_TOUR_STATE }),
            ...mapActions({ fetchAdapters: FETCH_ADAPTERS }),
        	configAdapter(adapterId) {
            	/*
            	    Fetch adapter requested to be configured asynchronously, before navigating to the
            	    configuration page, so it will return meanwhile
            	 */
                this.$router.push({path: `adapter/${adapterId}`})
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
    .adapters {
        .adapters-search {
            margin-bottom: 12px;
        }
        .adapters-table {
            height: calc(100vh - 212px);
            overflow: auto;
            .table {
                border-collapse: separate;
                border-spacing: 0 8px;
                font-size: 14px;
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
                            height: 3.6em;
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
                thead .table-row .row-data:nth-child(2) {
                    border-bottom-left-radius: 4px;
                    border-top-left-radius: 4px;
                }
                tbody .table-row:hover {
                    cursor: pointer;
                    transform: scale(1.02);
                }
            }

        }
    }
</style>