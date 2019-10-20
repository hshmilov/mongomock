<template>
  <x-page
    :class="{disabled: isReadOnly}"
    class="x-reports"
    title="Reports"
  >
    <x-table
      v-model="isReadOnly? undefined: selection"
      :on-click-row="navigateReport"
      module="reports"
      title="Saved Reports"
    >
      <template slot="actions">
        <x-safeguard-button
          v-if="hasSelection"
          :approve-text="numberOfSelections > 1 ? 'Remove Reports' : 'Remove Report'"
          link
          @click="remove"
        >
          <div slot="button-text">Remove</div>
          <div slot="message">
            The selected {{ numberOfSelections > 1 ? 'reports' : 'report' }} will be completely removed
            from the system.<br>
            Removing the {{ numberOfSelections > 1 ? 'reports' : 'report' }} is an irreversible action.<br>
            Do you wish to continue?
          </div>
        </x-safeguard-button>
        <x-button
          id="report_new"
          :disabled="isReadOnly"
          @click="navigateReport('new')"
        >+ New Report</x-button>
      </template>
    </x-table>
  </x-page>
</template>
<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xSafeguardButton from '../axons/inputs/SafeguardButton.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {REMOVE_REPORTS, FETCH_REPORT} from '../../store/modules/reports'

    export default {
        name: 'XReports',
        components: {xPage, xTable, xButton, xSafeguardButton},
        computed: {
            ...mapState({
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
            },
            numberOfSelections() {
                return this.selection.ids ? this.selection.ids.length : 0
            },
        },
        data() {
            return {
                selection: {
                  ids: [], include: true
                }
            }
        },
        methods: {
            ...mapActions({
                removeReports: REMOVE_REPORTS, fetchReport: FETCH_REPORT
            }),
            navigateReport(reportId) {
                this.fetchReport(reportId)
                this.$router.push({path: `/${this.name}/${reportId}`})
            },
            remove() {
                this.removeReports(this.selection)
                this.selection = {ids: [], include: true }
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