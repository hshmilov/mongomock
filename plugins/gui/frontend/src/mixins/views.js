import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
import { IS_EXPIRED } from '../store/getters'
import { UPDATE_DATA_VIEW } from '../store/mutations'
import { FETCH_DATA_CONTENT } from '../store/actions'
import { entities } from '../constants/entities'

export default {
  computed: {
    ...mapState({
      views (state) {
        return this.entityList.reduce((map, module) => {
          map[module] = state[module].views.saved.content.data
            .filter(view => view)
            .map((view) => {
              return { name: view.name, title: view.name, predefined: view.predefined }
            })
          return map
        }, {})
      },
      entityOptions (state) {
        if (!state.auth.currentUser.data) return {}
        let permissions = state.auth.currentUser.data.permissions
        return entities.filter(entity => {
          return permissions[entity.title] !== 'Restricted'
        })
      }
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED
    }),
    entityList () {
      return this.entityOptions.map(entity => entity.name)
    }
  },
  methods: {
    ...mapMutations({
      updateDataView: UPDATE_DATA_VIEW
    }),
    ...mapActions({
      fetchViews: FETCH_DATA_CONTENT
    }),
    fetchViewsHistory () {
      this.entityList.forEach(entity => {
        this.fetchViews({ module: `${entity}/views/history` })
      })
    },
    viewsCallback () {}
  },
  created () {
    if (this.isExpired) return
    let promises = []
    this.entityList.forEach(entity => {
      let module = `${entity}/views/saved`
      this.updateDataView({
        module, view: {
          query: {filter: '', expressions: []}
        }
      })
      promises.push(this.fetchViews({ module }))
    })
    Promise.all(promises).then(this.viewsCallback)
  }
}