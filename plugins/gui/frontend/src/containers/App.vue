<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!--Link for downloading files-->
        <a id="download-link"/>
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="userName || isDev">
            <side-bar-container class="print-exclude" @access-violation="notifyAccess" />
            <router-view/>
            <top-bar-container class="print-exclude" @access-violation="notifyAccess" />
            <x-tour-state />
            <modal v-if="accessMessage" @close="removeAccessMessage">
                <div slot="body">{{ accessMessage }}</div>
                <div slot="footer"><button class="x-btn" @click="removeAccessMessage">OK</button></div>
            </modal>
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
    import Modal from '../components/popover/Modal.vue'

    import { GET_USER} from '../store/modules/auth'
    import { FETCH_SYSTEM_CONFIG } from "../store/actions";
    import { FETCH_CONSTANTS } from "../store/modules/constants";
	import { mapState, mapActions } from 'vuex'
	import '../components/icons'


	export default {
        name: 'app',
        components: { LoginContainer, TopBarContainer, SideBarContainer, xTourState, Modal },
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
        data() {
             return {
                 accessMessage: ''
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
                getUser: GET_USER, fetchConfig: FETCH_SYSTEM_CONFIG, fetchConstants: FETCH_CONSTANTS
            }),
            fetchGlobalData() {
				this.fetchConfig()
                this.fetchConstants()
            },
            notifyAccess(name) {
                this.accessMessage = `You do not have permission to access the ${name} screen`
            },
            removeAccessMessage() {
                this.accessMessage = ''
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
