<template>
    <aside class="x-side-bar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <div class="x-user">
            <div class="x-user-profile">
                <img :src="auth.data.pic_name" />
                <h5>{{ `${auth.data.first_name} ${auth.data.last_name}` }}</h5>
            </div>
            <div class="x-user-actions">
                <a @click="logout" data-toggle="tooltip" title="Logout">
                    <svg-icon name="navigation/logout" height="16" :original="true"/>
                </a>
            </div>
        </div>
        <nav class="x-menu">
            <nested-nav-bar>
                <nested-nav-item route-name="Dashboard" router-path="/" icon-name="dashboard" :exact="true"/>
                <nested-nav-item route-name="Devices" icon-name="device">
                    <nested-nav-bar nest-level="1" class="collapse">
                        <nested-nav-item route-name="Saved Queries" router-path="/device/query/saved" />
                    </nested-nav-bar>
                </nested-nav-item>
                <nested-nav-item route-name="Users" icon-name="user">
                    <nested-nav-bar nest-level="1" class="collapse">
                        <nested-nav-item route-name="Saved Queries" router-path="/user/query/saved" />
                    </nested-nav-bar>
                </nested-nav-item>
                <nested-nav-item route-name="Alerts" icon-name="alert"/>
                <nested-nav-item route-name="Adapters" icon-name="adapter"/>
                <nested-nav-item route-name="Reports" icon-name="report"/>
            </nested-nav-bar>
        </nav>
    </aside>
</template>

<script>
    import '../../components/icons/navigation'

    import NestedNavBar from '../../components/menus/NestedNavBar.vue'
    import NestedNavItem from '../../components/menus/NestedNavItem.vue'
    import { LOGOUT } from '../../store/modules/auth'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'x-side-bar-container',
        components: { NestedNavBar, NestedNavItem },
        computed: mapState([ 'auth', 'interaction' ]),
        methods: mapActions({ logout: LOGOUT })
    }
</script>

<style lang="scss">
    .x-side-bar {
        position: fixed;
        width: 240px;
        transition: all ease-in 0.2s;
        height: 100%;
        z-index: 20;
        background: $theme-black;
        padding-bottom: 60px;
        display: flex;
        flex-flow: column;
        .x-user {
            flex: 0 1 auto;
            position: relative;
            font-size: $font-size-title;
            width: 100%;
            overflow-x: hidden;
            transition: all ease-in 0.2s;
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
        .x-menu {
            overflow: auto;
            flex: 1 0 auto;
            background: $theme-black;
            padding: 0px;
            padding-top: 30px;
            .nav-nest {
                transition: all ease-in 0.2s;
            }
            .nav-link.has-arrow::after {
                transition: all ease-in 0.2s;
                opacity: 1;
            }
        }
    }
    .x-side-bar.collapse {
        display: block;
        width: 60px;
        padding-bottom: 0;
        position: absolute;
        .x-user {
            .x-user-profile {
                text-align: left;
                h5 {
                    opacity: 0;
                }
            }
        }
        .x-menu {
            overflow: visible;
            .nav-nest .nav-link span {
                opacity: 0;
            }
            .nav-item {
                overflow: hidden;
                .nav-nest.collapse {
                    display: none;
                    transition: all ease-in 0.2s;
                }
                &:hover {
                    overflow: visible;
                    position: relative;
                    .nav-nest.collapse {
                        left: 56px;
                        margin-left: 0;
                        top: 0;
                        position: absolute;
                        background-color: $theme-black;
                        display: block;
                        .nav-link span {
                            transition: all ease-in 0.5s;
                            opacity: 1;
                        }
                    }
                }
            }
            .nav-link.has-arrow::after {
                opacity: 0;
            }
        }
    }


</style>