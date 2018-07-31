<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="userName || isDev">
            <side-bar-container class="print-exclude"/>
            <router-view/>
            <top-bar-container class="print-exclude"/>
            <x-tour-state />
        </template>
        <template v-else>
            <login-container />
        </template>
    </div>
</template>

<script>
    import TopBarContainer from './navigation/TopBarContainer.vue'
    import SideBarContainer from './navigation/SideBarContainer.vue'
    import LoginContainer from './auth/LoginContainer.vue'
	import xTourState from '../components/onboard/TourState.vue'

    import { GET_USER} from '../store/modules/auth'
    import { LOAD_PLUGIN_CONFIG } from "../store/modules/configurable";
	import { mapState, mapActions } from 'vuex'
	import '../components/icons'


	export default {
        name: 'app',
        components: { LoginContainer, TopBarContainer, SideBarContainer, xTourState },
        computed: {
            ...mapState({
                userName(state) {
                	return state.auth.data.user_name
                }
            }),
            isDev() {
				return process.env.NODE_ENV === 'development'
            },
            currentPage() {
            	return this.$route.fullPath
            }
		},
        watch: {
        	userName(newUserName) {
                if (newUserName) {
                	this.fetchGlobalData()
                }
            },
            currentPage() {
        		this.fetchGlobalData()
            }
        },
        methods: {
            ...mapActions({
                getUser: GET_USER, loadPluginConfig: LOAD_PLUGIN_CONFIG
            }),
            fetchGlobalData() {
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
        	this.getUser()
        }
    }
</script>

<style lang="scss">
    @import '../scss/app';
    @import '../scss/styles';
    @import '../scss/custom_styles';

    #app {
        height: 100vh;
    }
</style>
