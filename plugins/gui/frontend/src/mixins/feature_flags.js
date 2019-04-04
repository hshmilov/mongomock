import {mapState, mapMutations, mapActions} from 'vuex'
import {LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG} from '../store/modules/settings'


export default {
  computed: mapState({
    featureFlags (state) {
      if (!state.settings.configurable.gui || !state.settings.configurable.gui.FeatureFlags) return null
      return state.settings.configurable.gui.FeatureFlags.config
    }
  }),
  mounted() {
    let config = {
      pluginId: 'gui',
      configName: 'FeatureFlags'
    }
    this.changePluginConfig({
      fetching: false,
      error: '',
      data: {},
      ...config
    })
    this.loadPluginConfig(config)
  },
  methods: {
    ...mapActions({
      loadPluginConfig: LOAD_PLUGIN_CONFIG
    }),
    ...mapMutations({
      changePluginConfig: CHANGE_PLUGIN_CONFIG
    })
  }
}