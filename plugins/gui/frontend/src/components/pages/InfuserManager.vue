<template>
    <x-page title="Infuser Manager" style="height: 100%; margin-left: -26px;">
        <iframe style="margin-top: -56px; width: 100%; height: 100%" :src="`https://ptool-we.azurewebsites.net/pump-programming/pairing?token=${oktaIdToken}`"></iframe>
    </x-page>
</template>
<script>
    import xPage from '../axons/layout/Page.vue'
    import {mapState} from 'vuex'

    export default {
        name: "infuser-manager",
        components: { xPage },
        computed:{
            ...mapState(['auth']),
            oktaIdToken() {
                return this.auth.oktaIdToken.data
            },
        }
    }
</script>

<style lang="scss">

</style>