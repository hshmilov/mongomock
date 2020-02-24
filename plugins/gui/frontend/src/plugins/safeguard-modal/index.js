/* eslint-disable no-param-reassign */
import Safeguard from './Safeguard.vue';

const SafeguardPlugin = {
  install(Vue) {
    // create communication chanel to our plugin
    this.EventBus = new Vue();

    // make the x-safeguard globally registered
    Vue.component('XSafeguard', Safeguard);

    // expose global interface
    Vue.prototype.$safeguard = {
      show(params) {
        SafeguardPlugin.EventBus.$emit('show', params);
      },
    };
  },
};

export default SafeguardPlugin;
