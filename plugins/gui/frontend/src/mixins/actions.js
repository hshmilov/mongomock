import {mapState, mapMutations, mapActions} from 'vuex'
import {FETCH_ACTIONS, FETCH_SAVED_ACTIONS} from '../store/modules/enforcements'
import {UPDATE_EMPTY_STATE} from '../store/modules/onboarding'
import {FETCH_SYSTEM_CONFIG} from '../store/actions'

export default {
    computed: {
        ...mapState({
            actionsDef(state) {
                return state.enforcements.actions.data
            },
            savedActions(state) {
                return state.enforcements.savedActions.data
            },
            emptySettings(state) {
                return state.onboarding.emptyStates.settings
            },
            globalSettings(state) {
                if (!state.configuration || !state.configuration.data || !state.configuration.data.global) return
                return state.configuration.data.global
            }
        }),
        settingNames() {
            return Object.keys(this.emptySettings)
        },
        settingToActions() {
            return {
                mail: ['send_emails', 'send_email_to_entities'],
                syslog: ['notify_syslog'],
                httpsLog: ['send_https_log'],
                jira: ['create_jira_incident']
            }
        },
        anyEmptySettings() {
            return Object.values(this.emptySettings).find(value => value)
        }
    },
    methods: {
        ...mapMutations({
            updateEmptyStates: UPDATE_EMPTY_STATE
        }),
        ...mapActions({
            fetchActions: FETCH_ACTIONS, fetchSavedActions: FETCH_SAVED_ACTIONS, fetchConfig: FETCH_SYSTEM_CONFIG
        }),
        actionNameExists(name) {
            return this.savedActions.includes(name)
        },
        updateEmptySettings(name) {
            if (!this.globalSettings[name]) {
                this.updateEmptyStates({
                    settings: Object.keys(this.emptySettings).reduce((map, currentName) => {
                        map[currentName] = currentName === name
                        return map
                    }, {})
                })
            }
        },
        checkEmptySettings(action) {
            this.updateEmptySettings(this.settingNames
                .find(setting => this.settingToActions[setting].includes(action)))
        }
    },
    created() {
        this.fetchActions()
        this.fetchSavedActions()
        this.fetchConfig()
    }
}