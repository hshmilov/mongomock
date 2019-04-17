import {mapState, mapMutations, mapActions} from 'vuex'
import {FETCH_ACTIONS, FETCH_SAVED_ACTIONS} from '../store/modules/enforcements'
import {UPDATE_EMPTY_STATE} from '../store/modules/onboarding'
import {FETCH_SYSTEM_CONFIG} from '../store/actions'
import config from './config'

export default {
    mixins: [config],
    computed: {
        ...mapState({
            actionsDef(state) {
                return state.enforcements.actions.data
            },
            savedActions(state) {
                return state.enforcements.savedActions.data
            }
        }),
        settingToActions() {
            return {
                mail: ['send_emails', 'send_email_to_entities'],
                syslog: ['notify_syslog'],
                httpsLog: ['send_https_log'],
                jira: ['create_jira_incident']
            }
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
        }
    },
    created() {
        this.fetchActions()
        this.fetchSavedActions()
        this.fetchConfig()
    }
}