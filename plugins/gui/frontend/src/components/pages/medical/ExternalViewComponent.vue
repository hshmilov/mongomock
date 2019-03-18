<template>
    <x-page :title="title" :breadcrumbs="[{ title: 'Infuser Manager' ,path: { name: name}},{ title: name }]" style="height: 100%; margin-left: -26px;">
        <iframe style="margin-top: -56px; width: 100%; height: 100%" :src="`${urlWithToken}`"></iframe>
    </x-page>
</template>
<script>
    import xPage from '../../axons/layout/Page.vue'
    import {mapState} from 'vuex'

    export default {
        name: "external-view-component",
        props: [ "medicalUrl", "name" , "title"],
        components: { xPage },
        computed: {
            ...mapState([ 'auth', 'interaction' ]),
            urlWithToken() {
                if (this.auth.currentUser.data && this.auth.currentUser.data.oidc_data &&
                    this.auth.currentUser.data.oidc_data.is_account_manager && this.interaction.branch == 'Account')
                    return `https://ptool-we.azurewebsites.net/${this.medicalUrl}?token=${this.auth.currentUser.data.oidc_data.id_token}&lang=${this.interaction.language}&workspace=Account&groupName=${this.accountGroup.name}&groupId=${this.accountGroup.id}&groupList=${this.auth.currentUser.data.oidc_data.groups.map(item => item.id).join(',')}&timeStamp=${Date.now()}`
                if (this.auth.currentUser.data && this.auth.currentUser.data.oidc_data)
                    return `https://ptool-we.azurewebsites.net/${this.medicalUrl}?token=${this.auth.currentUser.data.oidc_data.id_token}&lang=${this.interaction.language}&workspace=Branch&groupName=${this.interaction.branch}&groupId=${this.branchId}&timeStamp=${Date.now()}`
                return ''
            },
            branchId(){
                if(this.auth.currentUser.data && this.auth.currentUser.data.oidc_data.groups){
                    let selectedGroup = this.auth.currentUser.data.oidc_data.groups.find(item=>
                        item.profile.name == this.interaction.branch)
                    if(selectedGroup)
                        return selectedGroup.id
                }
                return ''
            },
            accountGroup(){
                if(this.auth.currentUser.data.oidc_data.claims){
                    return {name: this.auth.currentUser.data.oidc_data.claims.account_name || '',
                        id: this.auth.currentUser.data.oidc_data.claims.account_guid || ''}
                }
                return {name: '', id: ''}
            }
        }
    }
</script>

<style lang="scss">

</style>

