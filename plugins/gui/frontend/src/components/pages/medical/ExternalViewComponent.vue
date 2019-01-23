<template>
    <x-page :title="title" :breadcrumbs="[{ title: 'Settings' ,path: { name: name}},{ title: name }]" style="height: 100%; margin-left: -26px;">
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
            ...mapState([ 'auth' ]),
            urlWithToken(){
                return `https://ptool-we.azurewebsites.net/${this.medicalUrl}?token=${this.auth.oidcIdToken.data}`
            }
        }
    }
</script>

<style lang="scss">

</style>

