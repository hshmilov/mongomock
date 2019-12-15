import Safeguard from './Safeguard.vue'

const SafeguardPlugin = {
    install(Vue, options) {
        // create communication chanel to our plugin
        this.EventBus = new Vue()

        // make the x-safeguard globally registered
        Vue.component('x-safeguard', Safeguard)

        // expose global interface
        Vue.prototype.$safeguard = {
            show(params) {
                SafeguardPlugin.EventBus.$emit('show', params)
            }
        }
    }
}

export default SafeguardPlugin