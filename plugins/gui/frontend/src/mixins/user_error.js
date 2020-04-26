import {mapState, mapMutations} from 'vuex'
import {INIT_ERROR} from '../store/modules/auth'
import { NOT_LOGGED_IN } from '@store/modules/auth';


export default {
  computed: mapState({
    prettyUserError(state) {
      if (state.auth.currentUser.error === NOT_LOGGED_IN) {
        return ''
      }

      return state.auth.currentUser.error
    }
  }),
  methods: mapMutations({
    initError: INIT_ERROR
  })
}
