<template>
    <div>
        <div class="x-search-insights">
            <x-search-input placeholder="Search by Host Name, User Name, MAC or IP..." v-model="searchValue"
                            @keydown.enter.native="onClick" :disabled="entitiesRestricted"
                            @click.native="notifyAccess"/>
            <button @click="onClick" class="x-btn right" :class="{ disabled: entitiesRestricted }">Search</button>
        </div>
        <x-access-modal v-model="blockedComponent"/>
    </div>
</template>

<script>
    import xSearchInput from './SearchInput.vue'
    import xAccessModal from '../popover/AccessModal.vue'

    import {mapState, mapMutations} from 'vuex'
    import {UPDATE_DATA_VIEW} from '../../../store/mutations'
    import {UPDATE_SEARCH_VALUE} from '../../../store/modules/explorer'
    import {entities} from '../../../constants/entities'

    export default {
        name: 'x-search-insights',
        components: {xSearchInput, xAccessModal},
        computed: {
            ...mapState({
                explorer(state) {
                    return state.explorer
                },
                entitiesRestricted(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Devices === 'Restricted' || user.permissions.Users === 'Restricted'
                }
            }),
            searchValue: {
                get() {
                    return this.explorer.searchValue
                },
                set(value) {
                    this.updateSearchValue(value)
                }
            },
            excludedFields() {
                return []
            }
        },
        data() {
            return {
                blockedComponent: ''
            }
        },
        methods: {
            ...mapMutations({
                updateDataView: UPDATE_DATA_VIEW, updateSearchValue: UPDATE_SEARCH_VALUE
            }),
            notifyAccess() {
                if (!this.entitiesRestricted) return
                this.blockedComponent = 'Devices and Users Search'
            },
            onClick() {
                if (this.entitiesRestricted) {
                    this.notifyAccess()
                    return
                }
                let expressions = this.searchValue.split(',')
                entities.forEach(entity => {
                    let patternParts = []
                    this.explorer[entity.name].view.fields.forEach(field => {
                        if (this.excludedFields.includes(field)) return
                        expressions.forEach(expression =>
                            patternParts.push(`${field} == regex("${expression.trim()}", "i")`))
                    })
                    this.updateDataView({
                        module: entity.name, section: 'explorer', view: {query: {filter: patternParts.join(' or ')}}
                    })
                })
                this.$emit('click')
            }
        }
    }
</script>

<style lang="scss">
    .x-search-insights {
        display: flex;
        width: 60vw;
        margin: auto;
        margin-bottom: 12px;

        .x-search-input {
            flex: 1 0 auto;
            border-radius: 16px 0 0 16px;

            &.focus {
                border-color: $theme-orange;
            }
        }

        .x-btn {
            border-radius: 0 16px 16px 0;
            background-color: $theme-orange;

        }
    }
</style>