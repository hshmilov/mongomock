<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!--Link for downloading files-->
        <a id="file-auto-download-link"></a>
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="userName || isDev">
            <side-bar-container class="print-exclude" @access-violation="notifyAccess" />
            <router-view/>
            <top-bar-container class="print-exclude" @access-violation="notifyAccess" />
            <x-tour-state />
            <x-access-modal v-model="blockedComponent" />
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
    import xAccessModal from '../components/popover/AccessModal.vue'

    import { GET_USER} from '../store/modules/auth'
    import { FETCH_DATA_FIELDS, FETCH_SYSTEM_CONFIG } from "../store/actions";
    import { FETCH_CONSTANTS, FETCH_FIRST_HISTORICAL_DATE, FETCH_ALLOWED_DATES } from "../store/modules/constants";
    import { UPDATE_WINDOW_WIDTH } from '../store/mutations'
    import { mapState, mapMutations, mapActions } from 'vuex'
    import { entities } from '../constants/entities'
	import '../components/icons'


	export default {
        name: 'app',
        components: {
            LoginContainer, TopBarContainer, SideBarContainer, xTourState, xAccessModal
        },
        computed: {
            ...mapState({
                userName(state) {
                	return state.auth.currentUser.data.user_name
                },
                userPermissions(state) {
                    return state.auth.currentUser.data.permissions
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
                 blockedComponent: ''
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
            ...mapMutations({ updateWindowWidth: UPDATE_WINDOW_WIDTH }),
            ...mapActions({
                getUser: GET_USER, fetchConfig: FETCH_SYSTEM_CONFIG, fetchConstants: FETCH_CONSTANTS,
                firstHistoricalDate: FETCH_FIRST_HISTORICAL_DATE, allowedDates: FETCH_ALLOWED_DATES,
                fetchDataFields: FETCH_DATA_FIELDS
            }),
            fetchGlobalData() {
				this.fetchConfig()
                this.fetchConstants()
                this.firstHistoricalDate()
                this.allowedDates()
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
    @import '../scss/styles';
    @import '../scss/custom_styles';

    #app {
        height: 100vh;
        width: 100vw;
        position: fixed;
    }
</style>
