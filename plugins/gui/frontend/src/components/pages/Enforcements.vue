<template>
    <x-page title="Enforcement Center" class="x-enforcements" :class="{disabled: isReadOnly}" beta>
        <x-table module="enforcements" @click-row="navigateEnforcement" title="Enforcement Sets" v-model="isReadOnly? undefined: selection">
            <template slot="actions">
                <x-button link v-if="hasSelection" @click="remove">Remove</x-button>
                <x-button @click="navigateEnforcement('new')" id="enforcement_new" :disabled="isReadOnly">+ New Enforcement</x-button>
                <x-button emphasize @click="navigateTasks">View Tasks</x-button>
            </template>
        </x-table>
    </x-page>
</template>


<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'
    import xButton from '../axons/inputs/Button.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {REMOVE_ENFORCEMENTS, FETCH_ENFORCEMENT} from '../../store/modules/enforcements'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-enforcements',
        components: {xPage, xTable, xButton},
        computed: {
            ...mapState({
                tourEnforcements(state) {
                    return state.onboarding.tourStates.queues.enforcements
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Enforcements === 'ReadOnly'
                }
            }),
            name() {
                return 'enforcements'
            },
            hasSelection() {
                return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
            }
        },
        data() {
            return {
                selection: {ids: []}
            }
        },
        methods: {
            ...mapMutations({changeState: CHANGE_TOUR_STATE}),
            ...mapActions({
                removeEnforcements: REMOVE_ENFORCEMENTS, fetchEnforcement: FETCH_ENFORCEMENT
            }),
            navigateEnforcement(enforcementId) {
                this.fetchEnforcement(enforcementId)
                this.$router.push({path: `/${this.name}/${enforcementId}`})
            },
            remove() {
                this.removeEnforcements(this.selection)
                this.selection = {ids: []}
            },
            navigateTasks() {
                this.$router.push({name: 'Tasks'})
            }
        },
        created() {
            if (this.tourEnforcements && this.tourEnforcements.length) {
                this.changeState({name: this.tourEnforcements[0]})
            }
        }
    }
</script>


<style lang="scss">
    .x-enforcements {
        .x-button {
            width: auto;
        }
    }
</style>