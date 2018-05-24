<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="userName || isDev">
            <top-bar-container class="print-exclude"/>
            <side-bar-container class="print-exclude"/>
            <router-view/>
        </template>
        <template v-else>
            <login-container :okta="okta_config"/>
        </template>
    </div>
</template>

<script>
    import TopBarContainer from './navigation/TopBarContainer.vue'
    import SideBarContainer from './navigation/SideBarContainer.vue'
    import LoginContainer from './auth/LoginContainer.vue'
    import {GET_OKTA_SETTINGS, GET_USER} from '../store/modules/auth'
    import { FETCH_ADAPTERS } from '../store/modules/adapter'
	import { mapState, mapActions } from 'vuex'
	import '../components/icons'
    import {LOAD_PLUGIN_CONFIG} from "../store/modules/configurable";

	export default {
        name: 'app',
        components: {
			LoginContainer,
			TopBarContainer, SideBarContainer },
        computed: {
            ...mapState({
                userName(state) {
                	return state.auth.data.user_name
                }
            }),
            isDev() {
				return process.env.NODE_ENV === 'development'
            }
		},
        data() {
            return {
                okta_config: {
                    okta_enabled: false
                }
            }
        },
        watch: {
        	userName(newUserName) {
                if (newUserName) {
                	this.fetchGlobalData()
                }
            }
        },
        methods: {
            ...mapActions({
                getUser: GET_USER, getOkta: GET_OKTA_SETTINGS, fetchAdapters: FETCH_ADAPTERS,
                loadPluginConfig: LOAD_PLUGIN_CONFIG
            }),
            fetchGlobalData() {
				this.fetchAdapters()
				this.loadPluginConfig({
					pluginId: 'gui',
					configName: 'GuiService'
				})
				this.loadPluginConfig({
					pluginId: 'core',
					configName: 'CoreService'
				})
            }
		},
        created() {
        	this.getUser().then((response) => {
        		if (response.status === 200) {
                    this.fetchGlobalData()
                }
            })
            this.getOkta().then(response => {
                if (response.status === 200) {
                    this.okta_config = response.data
                }
            })
        }
    }
</script>

<style lang="scss">
    @import '../assets/plugins/fonts/icons/style.css';
    @import '../scss/app';
    @import '../scss/styles';

    #app {
        height: 100vh;
    }
</style>
