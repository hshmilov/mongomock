/* eslint-disable no-param-reassign */
import MessageModal from './MessageModal.vue';

const MessageModalPlugin = {
  install(Vue) {
    // create communication chanel to our plugin
    this.EventBus = new Vue();

    // make the x-safeguard globally registered
    Vue.component('XMessageModal', MessageModal);

    // expose global interface
    Vue.prototype.$messageModal = {
      show(params) {
        MessageModalPlugin.EventBus.$emit('show', params);
      },
    };
  },
};

export default MessageModalPlugin;
