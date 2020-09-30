<template>
  <div class="x-empty-system">
    <XIcon
      family="illustration"
      class="icon_see-all"
      type="see_all"
    />
    <div class="system-title">
      SEE ALL TO SECURE ALL
    </div>
    <div class="content">Congratulations! You are one step closer to<br>having all your assets visible in one place.
    </div>
    <div class="footer">
      <XButton
        v-if="isUserAdmin"
        type="primary"
        @click="openGettingStarted"
      >
        SHOW ME HOW
      </XButton>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import { GettingStartedPubSub } from '../../App.vue';

import { IS_USER_ADMIN } from '../../../store/modules/auth';

export default {
  name: 'XEmptySystem',
  computed: {
    ...mapGetters({
      isUserAdmin: IS_USER_ADMIN,
    }),
  },
  methods: {
    openGettingStarted() {
      GettingStartedPubSub.$emit('getting-started-open-state');
    },
  },
};
</script>

<style lang="scss">
    .x-empty-system {
        text-align: center;

        .icon_see-all {
          font-size: 420px;
        }

        .system-title {
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
