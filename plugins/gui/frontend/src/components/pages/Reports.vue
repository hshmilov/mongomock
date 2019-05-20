<template>
    <x-page title="Reports" class="x-reports" :class="{disabled: isReadOnly}" >
        <x-table module="reports" @click-row="navigateReport" title="Saved Reports" v-model="isReadOnly? undefined: selection">
            <template slot="actions">
                <x-button link v-if="hasSelection" @click="remove">Remove</x-button>
                <x-button @click="navigateReport('new')" id="report_new" :disabled="isReadOnly">+ New Report</x-button>
            </template>
        </x-table>
    </x-page>
</template>
<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'
    import xButton from '../axons/inputs/Button.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {REMOVE_REPORTS, FETCH_REPORT} from '../../store/modules/reports'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-reports',
        components: {xPage, xTable, xButton},
        computed: {
            ...mapState({
                tourReports(state) {
                    return state.onboarding.tourStates.queues.reports
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Reports === 'ReadOnly'
                }
            }),
            name() {
                return 'reports'
            },
            hasSelection() {
                return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
            }
        },
        data() {
            return {
                selection: {ids: [], include: true}
            }
        },
        methods: {
            ...mapMutations({changeState: CHANGE_TOUR_STATE}),
            ...mapActions({
                removeReports: REMOVE_REPORTS, fetchReport: FETCH_REPORT
            }),
            navigateReport(reportId) {
                this.fetchReport(reportId)
                this.$router.push({path: `/${this.name}/${reportId}`})
            },
            remove() {
                this.removeReports(this.selection)
                this.selection = {ids: [], include: true}
            }
        },
        created() {
            if (this.tourReports && this.tourReports.length) {
                this.changeState({name: this.tourReports[0]})
            }
        }
    }
</script>


<style lang="scss">
    .x-reports {
        .x-button {
            width: auto;
        }
    }
</style>