<template>
    <x-dropdown size="sm" align="right" :arrow="false" ref="dropdown" class="x-medical-user-profile">
        <div slot="trigger">
            <img :src="userDetails.pic"/>
        </div>
        <x-menu slot="content">
            <div :title="userDetails.name" class="menu-item">
                <span class="hello-span">Hello,</span>{{userDetails.name}}</div>
            <div v-if="userDetails.isAdmin">
                <a @click="onManageUsers" title="Manage users">Manage Users</a>
            </div>
            <a @click="onLogout" title="Logout">
                <svg-icon name="navigation/logout" height="16" :original="true"/>
                <span>Log out</span>
            </a>
        </x-menu>
    </x-dropdown>
</template>

<script>
    import xDropdown from '../axons/popover/Dropdown.vue'
    import xMenu from '../axons/menus/Menu.vue'
    import {mapState, mapActions} from 'vuex'
    import {GET_LOGIN_OPTIONS, LOGOUT} from '../../store/modules/auth'

    export default {
        name: 'x-medical-user-profile',
        components: {xDropdown, xMenu},

        computed: {
            ...mapState({
                userDetails(state) {
                    if (!state.auth.currentUser.data.oidc_data || !state.auth.currentUser.data.oidc_data.claims)
                        return {}
                    return {
                        name: state.auth.currentUser.data.oidc_data.claims.name,
                        isAdmin: state.auth.currentUser.data.oidc_data.is_admin,
                        adminRedirectUrl: state.auth.currentUser.data.oidc_data.admin_redirect_url,
                        idToken: state.auth.currentUser.data.oidc_data.id_token,
                        pic: state.auth.currentUser.data.pic_name
                    }
                },
                loginOptions(state) {
                    return state.auth.loginOptions.data
                },
            })
        },
        methods: {
            ...mapActions({getLoginSettings: GET_LOGIN_OPTIONS, logout: LOGOUT}),
            onLogout() {
                if (window.location.pathname !== '/') {
                    this.$router.push('/')
                }
                let addition = `/oauth2/${this.loginOptions.okta.authorization_server}/v1/logout`
                addition += `?post_logout_redirect_uri=${this.loginOptions.okta.gui2_url}`
                addition += `&id_token_hint=${this.userDetails.idToken}`
                this.logout().then(document.location = this.loginOptions.okta.url + addition)
            },
            onManageUsers() {
                window.open(this.userDetails.adminRedirectUrl, '_blank');
            }
        },
        created() {
            if (!this.loginOptions) {
                this.getLoginSettings()
            }
        }
    }
</script>

<style lang="scss">
    .x-medical-user-profile {
        img {
            width: 30px;
            margin-bottom: 8px;
            border-radius: 100%;
            margin-top: 10px;
        }

        .x-menu {
            margin: 0 -8px 0 -4px;
        }

        .menu-item {
            padding: 3px 12px 3px 0;
            border-bottom: black solid 1px;
            margin-bottom: 10px;
            word-break: break-word;
        }

        .capital {
            text-transform: capitalize;
        }

        a {
            padding-right: 12px;
            line-height: 25px;
        }

        .hello-span {
            color: $theme-orange;
            margin-right: 5px;
        }

    }
</style>