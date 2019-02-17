
import {mapState, mapActions} from 'vuex'
import {FETCH_DATA_VIEWS} from '../store/actions'
import {entities} from '../constants/entities'

export default {
    computed: {
        ...mapState({
            views(state) {
                return this.entityList.reduce((map, module) => {
                    map[module] = state[module].views.saved.data.map((view) => {
                        return {name: view.name, title: view.name}
                    })
                    return map
                }, {})
            },
            entityOptions(state) {
                if (!state.auth.currentUser.data) return {}
                let permissions = state.auth.currentUser.data.permissions
                return entities.filter(entity => {
                    return permissions[entity.title] !== 'Restricted'
                })
            }
        }),
        entityList() {
            return this.entityOptions.map(entity => entity.name)
        }
    },
    methods: mapActions({
        fetchViews: FETCH_DATA_VIEWS
    }),
    created() {
        this.entityList.forEach(module => {
            this.fetchViews({module, type: 'saved'})
        })
    }
}