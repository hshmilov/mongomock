
import {mapState, mapActions} from 'vuex'
import {FETCH_DATA_VIEWS} from '../store/actions'
import {entities} from '../constants/entities'

export default {
    data () {
        return {
            viewsLoading: false
        }
    },
    computed: {
        ...mapState({
            views(state) {
                return this.entityList.reduce((map, module) => {
                    map[module] = state[module].views.saved.data.map((view) => {
                        return {name: view.name, title: view.name, predefined: view.predefined}
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
        },
        nonPredefinedCount() {
            let count = 0;
            this.entityList.forEach((module) => {
                count += this.views[module].filter((view) => {
                    return !view.predefined;
                }).length;
            });
            return count;
        }
    },
    methods: mapActions({
        fetchViews: FETCH_DATA_VIEWS
    }),
    created() {
        this.viewsLoading = true
        let promises = [];
        this.entityList.forEach(module => {
            promises.push(this.fetchViews({module, type: 'saved'}))
        })
        Promise.all(promises).then(() => {
            this.viewsLoading = false
        })
    }
}