<template>
    <x-select :options="userGroups" v-model="branch" placeholder="branch..."/>
</template>

<script>
    import xSelect from '../axons/inputs/Select.vue'
    import {mapState, mapMutations} from 'vuex'
    import {UPDATE_BRANCH} from '../../store/mutations'

    export default {
        name: "x-workspace-picker",
        components: {xSelect},
        computed: {
            ...mapState({
                userGroups(state) {
                    if (state.auth.currentUser.data.oidc_data && state.auth.currentUser.data.oidc_data.claims
                        && state.auth.currentUser.data.oidc_data.claims.groups) {
                        let filteredGroup = state.auth.currentUser.data.oidc_data.claims.groups.filter(group =>
                            group != 'Everyone' && group.toLowerCase().indexOf('_admins_') == -1
                            && group.toLowerCase().indexOf('_account_managers_') == -1
                        )
                        if(state.auth.currentUser.data.additional_userinfo &&
                            state.auth.currentUser.data.additional_userinfo.workspace &&
                            state.auth.currentUser.data.additional_userinfo.workspace == 'Account' &&
                            state.auth.currentUser.data.oidc_data &&
                            state.auth.currentUser.data.oidc_data.is_account_manager)
                        {
                            filteredGroup.push('Account')
                            return filteredGroup.map(group => {
                                return {
                                    name: group, title: group
                                }
                            })
                        }
                        else if(state.auth.currentUser.data.oidc_data.claims.organic_branch){
                            return [{
                                name: state.auth.currentUser.data.oidc_data.claims.organic_branch,
                                title: state.auth.currentUser.data.oidc_data.claims.organic_branch
                            }]
                        }
                    }
                    return []
                },
                currentBranch(state){
                    return state.interaction.branch
                }
            }),
            branch:{
                get(){
                    if(!this.userGroups.length)
                        return ''
                    return this.currentBranch ? this.currentBranch : this.userGroups[0].name
                },
                set(val){
                    this.updateBranch(val)
                }
            },
            userGroupsCount(){
                return this.userGroups.length
            }
        },
        watch:{
            userGroupsCount(newVal, oldVal){
                if(newVal && !oldVal)
                    this.updateBranch(this.userGroups[0].name)
            }
        },
        mounted(){
            if(!this.currentBranch && this.userGroups.length)
                this.updateBranch(this.userGroups[0].name)
        },
        methods: {
            ...mapMutations({
                updateBranch: UPDATE_BRANCH
            }),
        }
    }
</script>

<style scoped>

</style>