<template>
    <aside class="x-side-bar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <div class="x-user">
            <div class="x-user-profile">
                <img :src="auth.data.pic_name" />
                <h5>{{ `${auth.data.first_name} ${auth.data.last_name}` }}</h5>
            </div>
            <div class="x-user-actions">
                <a @click="logout" title="Logout">
                    <svg-icon name="navigation/logout" height="16" :original="true" />
                </a>
            </div>
        </div>
        <x-nested-nav>
            <x-nested-nav-item route-name="Dashboard" router-path="/" icon-name="dashboard" :exact="true" id="dashboard"/>
            <x-nested-nav-item route-name="Devices" icon-name="devices" id="devices">
                <x-nested-nav nest-level="1" class="collapse">
                    <x-nested-nav-item route-name="Saved Queries" router-path="/devices/query/saved" id="devices-queries"/>
                </x-nested-nav>
            </x-nested-nav-item>
            <x-nested-nav-item route-name="Users" icon-name="users" id="users">
                <x-nested-nav nest-level="1" class="collapse">
                    <x-nested-nav-item route-name="Saved Queries" router-path="/users/query/saved"/>
                </x-nested-nav>
            </x-nested-nav-item>
            <x-nested-nav-item route-name="Alerts" icon-name="alert" id="alerts" />
            <x-nested-nav-item route-name="Adapters" icon-name="adapter" id="adapters" />
            <x-nested-nav-item route-name="Reporting" icon-name="report" id="reports" />
        </x-nested-nav>
    </aside>
</template>

<script>
    import xNestedNav from '../../components/menus/NestedNav.vue'
    import xNestedNavItem from '../../components/menus/NestedNavItem.vue'

    import { LOGOUT } from '../../store/modules/auth'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'side-bar-container',
        components: { xNestedNav, xNestedNavItem },
        computed: mapState([ 'auth', 'interaction' ]),
        methods: mapActions({ logout: LOGOUT })
    }
</script>

<style lang="scss">
    .x-side-bar {
        position: fixed;
        top: 0;
        width: 240px;
        transition: all ease-in 0.2s;
        height: 100%;
        z-index: 100;
        background: $theme-black;
        padding: 60px 0;
        display: flex;
        flex-flow: column;
        .x-user {
            flex: 0 1 auto;
            position: relative;
            font-size: $font-size-title;
            width: 100%;
            overflow-x: hidden;
            transition: all ease-in 0.2s;
            margin-bottom: 48px;
            .x-user-profile {
                text-align: center;
                margin: 0 auto;
                padding: 10px 0 5px 0;
                border-radius: 100%;
                width: 240px;
                img {
                    width: 60px;
                    margin-bottom: 8px;
                    border-radius: 100%;
                }
                h5 {
                    color: $theme-white;
                    margin-bottom: 0;
                    transition: all ease-in 0.2s;
                }
            }
            .x-user-actions {
                padding: 4px 0px;
                position: relative;
                text-align: center;
                > a {
                    color: $grey-4;
                    padding: 0 4px;
                    .svg-fill {  fill: $grey-4;  }
                    .svg-stroke {  stroke: $grey-4;  }
                    &:hover {
                        color: $theme-white;
                        .svg-fill {  fill: $theme-white;  }
                        .svg-stroke {  stroke: $theme-white;  }
                    }
                    &:after {  display: none;  }
                }
            }
        }
        > .x-nested-nav > .x-nested-nav-item {
            border-left: 2px solid transparent;
            &.active {
                border-left: 2px solid $theme-orange;
            }
            .x-nested-nav {
                display: none;

            }
            &.active > .x-nested-nav {
                display: block;
            }
        }
    }
    .x-side-bar.collapse {
        display: block;
        width: 60px;
        padding-bottom: 0;
        .x-user {
            .x-user-profile {
                text-align: left;
                h5 {
                    opacity: 0;
                }
            }
        }
    }


</style>