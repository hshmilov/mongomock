<template>
    <div class="login" v-if="!user.data.user_name && !user.fetching">
        <div class="header">
            <svg-icon name="logo/logo" height="30" :original="true" class="navbar-logo"></svg-icon>
            <div class="title">Login</div>
        </div>
        <div class="error-text">{{user.error}}</div>
        <generic-form :schema="schema" v-model="credentials" submitLabel="Login" @submit="login" :vertical="true"></generic-form>
    </div>
</template>

<script>
    import GenericForm from '../../components/GenericForm.vue'
    import { LOGIN } from '../../store/modules/user'
	import '../../components/icons/logo'
    import { mapState, mapActions } from 'vuex'

	export default {
		name: 'login-container',
        components: { GenericForm },
        computed: {
			schema() {
				return [
                    { path: 'user_name', name: 'User Name', control: 'text'},
                    { path: 'password', name: 'Password', control: 'password'}
                ]
            },
            ...mapState(['user'])
        },
        data() {
			return {
				credentials: {
					user_name: '',
                    password: ''
                }
            }
        },
        methods: mapActions({
            login: LOGIN
		})
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .login {
        padding: 200px;
        height: 100vh;
        .header {
            margin-bottom: 20px;
            .title {
                display: inline-block;
                margin-left: 20px;
                font-size: 20px;
                color: $color-theme-light;
            }
        }
    }
</style>