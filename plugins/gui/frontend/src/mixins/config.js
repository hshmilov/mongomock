import {mapState, mapMutations, mapActions} from 'vuex'
import {UPDATE_EMPTY_STATE} from '../store/modules/onboarding'
import {FETCH_SYSTEM_CONFIG} from '../store/actions'

export default {
    computed: {
        ...mapState({
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
                mail: ['send_emails', 'send_email_to_entities']
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
            fetchConfig: FETCH_SYSTEM_CONFIG
        }),
        updateEmptySettings(name) {
            if (!this.globalSettings[name]) {
                if(this.emptySettings[name]){
                    setTimeout(() => {
                        this.updateEmptyStates({
                            settings: Object.keys(this.emptySettings).reduce((map, currentName) => {
                                map[currentName] = currentName === name ? false : this.emptySettings[currentName]
                                return map
                            }, {})
                        })
                        setTimeout(() => {
                            this.updateEmptyStates({
                                settings: Object.keys(this.emptySettings).reduce((map, currentName) => {
                                    map[currentName] = currentName === name
                                    return map
                                }, {})
                            })
                        })
                    })
                }
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
        this.fetchConfig()
    }
}