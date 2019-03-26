import {mapState, mapActions} from 'vuex'
import {LOAD_PLUGIN_CONFIG} from '../store/modules/settings'


export default {
  computed: mapState({
    featureFlags(state) {
      if (!state.settings.configurable.gui || !state.settings.configurable.gui.FeatureFlags) return null
      return state.settings.configurable.gui.FeatureFlags.config
    }
  }),
  mounted() {
    this.loadPluginConfig({
      pluginId: 'gui',
      configName: 'FeatureFlags'
    })
  },
  methods: mapActions({
    loadPluginConfig: LOAD_PLUGIN_CONFIG
  })
}