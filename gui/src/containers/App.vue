<template>
    <!--
        App structure includes fixed navigation containing header and menu bars
        with changing content, according to chosen route
    -->
    <div id="app">
        <!-- Nested navigation linking to routes defined in router/index.js -->
        <top-bar-container></top-bar-container>
        <side-bar-container></side-bar-container>
        <router-view></router-view>
    </div>
</template>

<script>
    import TopBarContainer from './navigation/TopBarContainer.vue'
    import SideBarContainer from './navigation/SideBarContainer.vue'
    import { mapState, mapGetters } from 'vuex'

    export default {
        name: 'app',
        components: { TopBarContainer, SideBarContainer }
    }
</script>

<style lang="scss">
    @import '../assets/plugins/fonts/icons/style.css';
    @import '../assets/plugins/css/bootstrap.min.css';
    @import '../assets/plugins/css/animate.css';
    @import '/node_modules/vue2-scrollbar/dist/style/vue2-scrollbar.css';
    @import '../scss/app';
</style>
