<template>
    <x-page title="alerts" class="x-alerts" :class="{disabled: isReadOnly}">
        <x-table module="alerts" title="Alerts" @click-row="configAlert" id-field="uuid"
                 v-model="isReadOnly? undefined: selection" ref="table">
            <template slot="actions" v-if="!isReadOnly">
                <div v-if="hasSelection" @click="removeAlerts" class="x-btn link">Remove</div>
                <div @click="createAlert" class="x-btn" id="alert_new">+ New Alert</div>
            </template>
        </x-table>
    </x-page>
</template>


<script>
    import xPage from '../axons/layout/Page.vue'
    import xTable from '../neurons/data/Table.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {ARCHIVE_ALERTS, FETCH_ALERT} from '../../store/modules/alerts'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-alerts',
        components: {xPage, xTable},
        computed: {
            ...mapState({
                tourAlerts(state) {
                    return state.onboarding.tourStates.queues.alerts
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Alerts === 'ReadOnly'
                }
            }),
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
            ...mapActions({fetchAlert: FETCH_ALERT, archiveAlerts: ARCHIVE_ALERTS}),
            configAlert(alertId) {
                /*
                    Fetch the requested alerts configuration and navigate to configuration page with the id, to load it
                 */
                if (!alertId || this.isReadOnly) {
                    return
                }
                this.fetchAlert(alertId)
                this.$router.push({path: `alerts/${alertId}`})
            },
            createAlert() {
                if (this.isReadOnly) {
                    return
                }
                this.fetchAlert()
                this.$router.push({path: '/alerts/new'})
            },
            removeAlerts() {
                if (this.isReadOnly) {
                    return
                }
                this.archiveAlerts(this.selection)
            }
        },
        created() {
            if (this.tourAlerts && this.tourAlerts.length) {
                this.changeState({name: this.tourAlerts[0]})
            }
        }
    }
</script>


<style lang="scss">
    .x-alerts {
        .x-data-table {
            height: 100%;
        }

        .disabled {
            .x-striped-table .clickable:hover {
                cursor: default;
                box-shadow: none;
            }
        }
    }
</style>