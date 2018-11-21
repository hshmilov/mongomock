<template>
    <div class="x-user-role-container">
        <div class="header">
            <h4 class="title">Users and Roles</h4>
            <button class="x-btn" :class="{ disabled: readOnly }" id="config-roles" @click="openRoles">Roles</button>
            <button class="x-btn" :class="{ disabled: readOnly }" id="create-user" @click="openCreateUser">+ New User</button>
        </div>
        <div v-for="user in users" class="user">
            <div class="user-details">
                <img :src="user.pic_name" class="user-details-profile"/>
                <div>
                    <div class="user-details-title">{{ user.user_name }} <span v-if="user.first_name.length > 0 || user.last_name.length > 0"> - {{ user.first_name}} {{ user.last_name }}</span></div>
                    <div>{{ user.source }}</div>
                </div>
            </div>
            <div class="user-permissions" v-if="!user.admin && !isCurrentUser(user)">
                <div class="user-role">
                    <label>User Role:</label>
                    <x-select :options="roleOptions" :searchable="true" placeholder="Custom"
                              v-model="user.role_name" @input="syncPermissions($event, user)" size="sm" />
                </div>
                <h5 v-if="user.role_name !== 'Admin'">Permissions</h5>
                <x-schema-form v-if="user.role_name !== 'Admin'" :schema="permissionSchema" v-model="user.permissions"
                               @input="syncRole(user)" :read-only="readOnly"/>
                <button class="x-btn link" id="user-settings-remove" :class="{ disabled: readOnly }"
                        @click="openRemoveUser(user)">Remove</button>
                <button class="x-btn link" id="user-settings-save" :class="{ disabled: readOnly }"
                        @click="savePermissions(user)">Save</button>
            </div>
        </div>
        <x-modal v-if="userToCreate" @close="closeCreateUser" @confirm="performCreateUser" approve-text="Create User">
            <div slot="body">
                <x-schema-form :schema="userSchema" v-model="userToCreate"/>
            </div>
        </x-modal>
        <x-modal v-if="userToRemove" @close="closeRemoveUser" @confirm="performRemoveUser" approve-text="Remove User">
            <div slot="body">
                <div>You are about to remove the user {{ userToRemove.user_name }}.</div>
                <div>This user will no longer be able to login to the system.</div>
                <div>Are you sure?</div>
            </div>
        </x-modal>
        <x-modal v-if="rolesConfig.data" title="Manage Roles" class="roles-container" @close="closeRoles">
            <div slot="body">
                <div class="roles-default">
                    <label>New external identity provider user default role</label>
                    <x-select :options="roleOptionsCustom" :searchable="true" :value="defaultRole" @input="saveDefaultRole" />
                </div>
                <label>Role</label>
                <x-select :options="roleOptionsCustom" :searchable="true" placeholder="New"
                          v-model="rolesConfig.selected" @input="updateRoleData" class="select-role" />
                <label>Name</label>
                <input type="text" class="name-role" v-model="rolesConfig.data.name" />
                <x-schema-form :schema="permissionSchema" v-model="rolesConfig.data.permissions" :read-only="readOnly"/>
                <button id="save-role-button" class="x-btn link" @click="saveRole">Save</button>
                <button v-if="rolesConfig.selected" id="remove-role-button" class="x-btn link" @click="performRemoveRole">Remove</button>
            </div>
            <div slot="footer">
                <button class="x-btn" @click="closeRoles">Done</button>
            </div>
        </x-modal>
    </div>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xModal from '../../components/popover/Modal.vue'
    import xSelect from '../../components/inputs/Select.vue'

    import { mapState, mapActions } from 'vuex'
    import {
        GET_ALL_USERS, CREATE_USER, REMOVE_USER, CHANGE_PERMISSIONS,
        GET_ALL_ROLES, CREATE_ROLE, REMOVE_ROLE, CHANGE_ROLE,
        GET_DEFAULT_ROLE, UPDATE_DEFAULT_ROLE
    } from '../../store/modules/auth'

    export default {
        name: 'x-user-role-container',
        components: {
            xSchemaForm, xModal, xSelect
        },
        props: { readOnly: { default: false } },
        computed: {
            ...mapState({
                users(state) {
                    return state.auth.allUsers.data
                },
                roles(state) {
                    return state.auth.allRoles.data
                },
                currentUser(state) {
                    return state.auth.currentUser.data
                },
                permissionLevels(state) {
                    if (!state.constants.constants.permission_levels) return []
                    return _.map(state.constants.constants.permission_levels, (a, b) => {
                        return {
                            title: a, name: b
                        }
                    })
                },
                permissionsDefault(state) {
                    if (!state.constants.constants.permission_types) return []
                    return Object.keys(state.constants.constants.permission_types).reduce((map, item) => {
                        if (item === 'Dashboard') {
                            map[item] = 'ReadOnly'
                        } else {
                            map[item] = 'Restricted'
                        }
                        return map
                    }, {})
                },
                defaultRole(state) {
                    return state.auth.defaultRole.data
                }
            }),
            permissionSchema() {
                return {
                    items: [
                        this.permissionSchemeItem('Dashboard', ['Restricted']),
                        this.permissionSchemeItem('Devices'),
                        this.permissionSchemeItem('Users'),
                        this.permissionSchemeItem('Adapters'),
                        this.permissionSchemeItem('Alerts'),
                        this.permissionSchemeItem('Reports'),
                        this.permissionSchemeItem('Settings'),
                    ],
                    required: [
                        'Settings', 'Adapters', 'Users', 'Devices', 'Alerts', 'Dashboard', 'Reports'
                    ],
                    type: 'array'
                }
            },
            userSchema() {
                return {
                    type: 'array', items: [{
                        name: 'user_name',
                        title: 'Username',
                        type: 'string',
                    }, {
                        name: 'password',
                        title: 'Password',
                        type: 'string',
                        format: 'password'
                    }, {
                        name: 'first_name',
                        title: 'First name',
                        type: 'string'
                    }, {
                        name: 'last_name',
                        title: 'Last name',
                        type: 'string'
                    }, {
                        name: 'role_name',
                        title: 'Role',
                        type: 'string',
                        enum: this.roles.map(item => item.name)
                    }], required: ['user_name', 'password']
                }
            },
            newUserTemplate() {
                return this.userSchema.items.reduce((map, item) => {
                    map[item.name] = ''
                    return map
                }, {})
            },
            permissionsByRole() {
                return this.roles.reduce((map, role) => {
                    map[role.name] = role.permissions
                    return map
                }, {})
            },
            roleOptions() {
                if (!this.roles) return []
                return this.roles.map(role => {
                    return {
                        name: role.name, title: role.name
                    }
                })
            },
            roleOptionsCustom() {
                return this.roleOptions.filter(item => item.name !== 'Admin')
            },
            rolesConfigName() {
                if (!this.rolesConfig.data) return ''
                return this.rolesConfig.data.name
            }
        },
        data() {
            return {
                userToCreate: null,
                userToRemove: null,
                rolesConfig: {
                    selected: '',
                    data: null
                }
            }
        },
        watch: {
            rolesConfigName(newName) {
                if (newName === this.rolesConfig.selected) return
                this.rolesConfig.selected = ''
            }
        },
        methods: {
            ...mapActions({
                getAllUsers: GET_ALL_USERS, changePermissions: CHANGE_PERMISSIONS,
                createUser: CREATE_USER, removeUser: REMOVE_USER,
                getAllRoles: GET_ALL_ROLES, changeRole: CHANGE_ROLE,
                createRole: CREATE_ROLE, removeRole: REMOVE_ROLE,
                getDefaultRole: GET_DEFAULT_ROLE, updateDefaultRole: UPDATE_DEFAULT_ROLE
            }),
            permissionSchemeItem(name, exclude = []) {
                let currentPermissionTypes = this.permissionLevels
                if (exclude.length) {
                    currentPermissionTypes = currentPermissionTypes.filter(type => !exclude.includes(type.name))
                }
                return {
                    name, title: name, type: "string",
                    enum: currentPermissionTypes, default: 'Restricted',
                }
            },
            openCreateUser() {
                if (this.readOnly) return
                this.userToCreate = { ...this.newUserTemplate }
            },
            performCreateUser() {
                if (this.readOnly) return
                this.createUser(this.userToCreate).then(response => {
                    this.$emit('toast', (response && response.status === 200? 'User created.' : response.data.message))
                    this.getAllUsers()
                }).catch(error => this.$emit('toast', error.response.data.message))
                this.closeCreateUser()
            },
            closeCreateUser() {
                this.userToCreate = null
            },
            savePermissions(user) {
                if (this.readOnly) return
                this.changePermissions({
                    uuid: user.uuid, role_name: user.role_name, permissions: user.permissions
                }).then(response => {
                    this.$emit('toast', (response && response.status === 200? 'User permissions saved.' : response.data.message))
                }).catch(error => this.$emit('toast', error.response.data.message))
            },
            openRemoveUser(user) {
                if (this.readOnly) return
                this.userToRemove = user
            },
            performRemoveUser() {
                this.removeUser({
                    uuid: this.userToRemove.uuid
                }).then(response => {
                    this.$emit('toast', (response.status === 200? 'User removed.' : response.data.message))
                    this.getAllUsers()
                }).catch(error => this.$emit('toast', error.response.data.message))
                this.userToRemove = null
            },
            closeRemoveUser() {
                this.userToRemove = null
            },
            syncPermissions(roleName, user) {
                user.permissions = this.permissionsByRole[roleName]
            },
            syncRole(user) {
                user.role_name = ''
            },
            openRoles() {
                if (this.readOnly) return
                this.rolesConfig.data = {
                    name: '', permissions: { ...this.permissionsDefault }
                }
            },
            saveRole() {
                if (!this.rolesConfig.data.name) return
                let saveFunc = (this.rolesConfig.selected) ? this.changeRole : this.createRole
                saveFunc(this.rolesConfig.data).then(response => {
                    this.$emit('toast', (response.status === 200? 'Role saved.' : response.data.message))
                    this.getAllRoles()
                    this.getAllUsers()
                }).catch(error => this.$emit('toast', error.response.data.message))
            },
            performRemoveRole() {
                this.removeRole({
                    name: this.rolesConfig.selected
                }).then(response => {
                    this.$emit('toast', (response.status === 200? 'Role removed.' : response.data.message))
                    this.rolesConfig.data = {
                        name: '', permissions: { ...this.permissionsDefault }
                    }
                    this.getAllRoles()
                    this.getAllUsers()
                }).catch(error => this.$emit('toast', error.response.data.message))
            },
            closeRoles() {
                this.rolesConfig.data = null
                this.rolesConfig.selected = ''
            },
            updateRoleData(name) {
                this.rolesConfig.data = {
                    name, permissions: { ...this.permissionsByRole[name] }
                }
            },
            saveDefaultRole(name) {
                this.updateDefaultRole({ name }).then(response => {
                    this.$emit('toast', (response && response.status === 200? 'Default Role saved.' : response.data.message))
                    this.getDefaultRole()
                })
            },
            isCurrentUser(user) {
                return user.user_name === this.currentUser.user_name && user.source === this.currentUser.source
            }
        },
        created() {
            this.getAllUsers()
            this.getAllRoles()
            this.getDefaultRole()
        }
    }
</script>

<style lang="scss">
    .x-user-role-container {
        .header {
            display: flex;
            align-items: center;
            .title {
                flex: 1 0 auto;
            }
        }
        #config-roles {
            margin-right: 12px;
        }
        .user {
            margin-bottom: 24px;
            .user-details {
                display: flex;
                .user-details-profile {
                    height: 60px;
                    margin-right: 8px;
                }
                .user-details-title {
                    font-weight: 400;
                    font-size: 16px;
                }
            }
            .user-permissions {
                text-align: right;
                margin-top: 12px;
                .user-role {
                    display: flex;
                    align-items: center;
                    .x-select {
                        margin-left: 12px;
                        text-align: left;
                    }
                }
                h5 {
                    margin: 12px 0;
                    text-align: left;
                }
            }
        }
        .schema-form {
            text-align: left;
            .array {
                grid-template-columns: 1fr 1fr 1fr;
            }
            .error {
                display: none;
            }
        }
        .roles-container {
            .x-select.select-role {
                width: 66%;
                margin-bottom: 12px;
            }
            .name-role {
                width: 66%;
                display: block;
                margin-bottom: 12px;
            }
            .x-btn.link {
                padding-left: 0;
            }
            .roles-default {
                margin: 0 -12px 12px;
                padding: 0 12px 24px;
                border-bottom: 1px solid $theme-blue;
            }
        }
    }
</style>