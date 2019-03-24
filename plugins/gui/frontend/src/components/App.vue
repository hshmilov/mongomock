<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app" v-if="fetchedLoginStatus">
        <!--Link for downloading files-->
        <a id="file-auto-download-link"></a>
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="userName">
            <x-side-bar class="print-exclude" @access-violation="notifyAccess" />
            <router-view/>
            <x-top-bar class="print-exclude" @access-violation="notifyAccess" />
            <x-tour-state />
            <x-access-modal v-model="blockedComponent" />
        </template>
        <template v-else>
            <x-signup />
            <x-login />
        </template>
    </div>
</template>

<script>
    import xTopBar from './networks/navigation/TopBar.vue'
    import xSideBar from './networks/navigation/SideBar.vue'
    import xLogin from './networks/navigation/Login.vue'
	import xTourState from './networks/onboard/TourState.vue'
    import xAccessModal from './neurons/popover/AccessModal.vue'
    import xSignup from './pages/Signup.vue'
    import {GET_USER} from '../store/modules/auth'
    import {FETCH_DATA_FIELDS, FETCH_SYSTEM_CONFIG} from '../store/actions'
    import {FETCH_CONSTANTS} from '../store/modules/constants'
    import {UPDATE_WINDOW_WIDTH} from '../store/mutations'
    import { mapState, mapMutations, mapActions } from 'vuex'
    import { entities } from '../constants/entities'

	import './axons/icons'


	export default {
        name: 'app',
        components: {
            xSignup, xLogin, xTopBar, xSideBar, xTourState, xAccessModal
        },
        computed: {
            ...mapState({
                fetchedLoginStatus(state) {
                    return Object.keys(state.auth.currentUser.data).length > 0 || state.auth.currentUser.error
                },
                userName(state) {
                	return state.auth.currentUser.data.user_name
                },
                userPermissions(state) {
                    return state.auth.currentUser.data.permissions
                }
            })
		},
        data() {
             return {
                 blockedComponent: ''
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
            ...mapMutations({ updateWindowWidth: UPDATE_WINDOW_WIDTH }),
            ...mapActions({
                getUser: GET_USER, fetchConfig: FETCH_SYSTEM_CONFIG, fetchConstants: FETCH_CONSTANTS,
                fetchDataFields: FETCH_DATA_FIELDS,
            }),
            fetchGlobalData() {
				this.fetchConfig()
                this.fetchConstants()
                entities.forEach(entity => {
                    if (this.entityRestricted(entity.title)) return
                    this.fetchDataFields({module: entity.name})
                })
            },
            notifyAccess(name) {
                this.blockedComponent = name
            },
            entityRestricted(entity) {
                return this.userPermissions[entity] === 'Restricted'
            }
		},
        created() {
        	this.getUser()
        },
        mounted() {
            this.$nextTick(function() {
                window.addEventListener('resize', this.updateWindowWidth)
                //Init
                this.updateWindowWidth()
            })
        }
    }
</script>

<style lang="scss">
    @import '../assets/scss/styles';
    @import '../assets/scss/custom_styles';

    #app {
        height: 100vh;
        width: 100vw;
        position: fixed;
    }
</style>
