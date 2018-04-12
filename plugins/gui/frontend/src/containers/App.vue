<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <template v-if="auth.data.user_name">
            <top-bar-container></top-bar-container>
            <side-bar-container></side-bar-container>
            <router-view></router-view>
        </template>
        <template v-else>
            <login-container></login-container>
        </template>
    </div>
</template>

<script>
    import TopBarContainer from './navigation/TopBarContainer.vue'
    import SideBarContainer from './navigation/SideBarContainer.vue'
    import LoginContainer from './auth/LoginContainer.vue'
    import { GET_USER } from '../store/modules/auth'
    import { FETCH_ADAPTERS } from '../store/modules/adapter'
    import { FETCH_SETTINGS } from '../store/modules/settings'
	import { mapState, mapActions } from 'vuex'

    export default {
        name: 'app',
        components: {
			LoginContainer,
			TopBarContainer, SideBarContainer },
        computed: mapState(['auth']),
        methods: mapActions({
            getUser: GET_USER,
            fetchAdapters: FETCH_ADAPTERS,
            fetchSettings: FETCH_SETTINGS
        }),
        created() {
        	this.getUser().then((response) => {
        		if (response.status === 200) {
                    this.fetchAdapters()
                    this.fetchSettings()
                }
            })
        }
    }
</script>

<style lang="scss">
    @import '../assets/plugins/fonts/icons/style.css';
    @import '../assets/plugins/css/bootstrap.min.css';
    @import '../scss/app';
    @import '../scss/styles';

    #app {
        height: 100vh;
    }
</style>
