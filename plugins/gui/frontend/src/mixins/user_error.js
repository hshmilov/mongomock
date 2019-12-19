import {mapState, mapMutations} from 'vuex'
import {INIT_ERROR} from '../store/modules/auth'


export default {
  computed: mapState({
    prettyUserError(state) {
      if (state.auth.currentUser.error === 'Not logged in') {
        return ''
      }

      if(this.$route.query.timeout){
        return 'Session timed out'
      }
      return state.auth.currentUser.error
    }
  }),
  methods: mapMutations({
    initError: INIT_ERROR
  })
}
