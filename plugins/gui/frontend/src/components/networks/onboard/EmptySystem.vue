<template>
    <div class="x-empty-system">
        <svg-icon name="illustration/see_all" :original="true" height="420"/>
        <div class="title">SEE ALL TO SECURE ALL</div>
        <div class="content">Congratulations! You are one step closer to<br>having all your assets visible in one place.
        </div>
        <div class="footer">
            <x-button v-if="isUserAdmin" @click="openGettingStarted">SHOW ME HOW</x-button>
        </div>
    </div>
</template>

<script>
    import { mapGetters } from 'vuex'
    import xButton from '../../axons/inputs/Button.vue'
    import { GettingStartedPubSub } from '../../App.vue'

    import { IS_USER_ADMIN } from '../../../store/modules/auth'

    export default {
        name: 'x-empty-system',
        components: {xButton},
        computed: {
            ...mapGetters({
                isUserAdmin: IS_USER_ADMIN,
            }),
        },
        methods: {
            openGettingStarted() {
                GettingStartedPubSub.$emit('getting-started-open-state')
            }
        }
    }
</script>

<style lang="scss">
    .x-empty-system {
        text-align: center;

        .title {
            font-size: 24px;
            color: $theme-orange;
            margin-top: 48px;
            margin-bottom: 24px;
        }

        .content {
            margin-bottom: 56px;
        }

        .footer {
            text-align: center;

            .x-button {
                width: auto;
            }
        }
    }
</style>