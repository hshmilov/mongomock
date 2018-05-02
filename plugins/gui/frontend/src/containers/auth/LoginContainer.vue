<template>
    <div class="login-container" v-if="!auth.data.user_name && !auth.fetching">
        <div class="login">
            <div class="header">
                <svg-icon name="logo/logo" height="36" :original="true"></svg-icon>
                <svg-icon name="logo/axonius" height="20" :original="true" class="logo-subtext"></svg-icon>
            </div>
            <div class="body">
                <h3 class="title">Login</h3>
                <x-schema-form :schema="schema" v-model="credentials" @input="initError" @validate="updateValidity"
                               @submit="onLogin" :error="auth.error"/>
                <button class="x-btn" :class="{disabled: !complete}" @click="onLogin">Login</button>
            </div>
        </div>
    </div>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import { LOGIN, INIT_ERROR } from '../../store/modules/auth'
	import '../../components/icons/logo'
    import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'login-container',
        components: { xSchemaForm },
        computed: {
			schema() {
				return {
					type: 'array', items: [
						{name: 'user_name', title: 'User Name', type: 'string'},
						{name: 'password', title: 'Password', type: 'string', format: 'password'}
					], required: ['user_name', 'password']
				}
            },
            ...mapState(['auth'])
        },
        data() {
			return {
				credentials: {
					user_name: '',
                    password: ''
                },
                complete: false
            }
        },
        methods: {
            ...mapMutations({ initError: INIT_ERROR }),
            ...mapActions({ login: LOGIN }),
            updateValidity(valid) {
            	this.complete = valid
            },
            onLogin() {
            	if (!this.complete) return
                this.login(this.credentials)
            }
		}
	}
</script>

<style lang="scss">
    .login-container {
        background: url('/src/assets/images/general/login_bg.png') center;
        height: 100vh;
        padding-top: 20vh;
        .login {
            width: 30vw;
            min-width: 300px;
            margin: auto;
            border-radius: 4px;
            background-color: $grey-1;
            display: flex;
            flex-flow: column;
            justify-content: center;
            .header {
                height: 128px;
                display: flex;
                flex-flow: column;
                justify-content: center;
            }
            .body {
                background-color: white;
                flex: 1 0 auto;
                padding: 48px;
                border-radius: 4px;
                .schema-form {
                    .object {
                        width: 100%;
                    }
                    .item {
                        width: 100%;
                    }
                }
                .x-btn {
                    width: 100%;
                }
            }

        }
    }
</style>