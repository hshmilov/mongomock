<template>
  <XPage
    :breadcrumbs="[
      {title: 'notifications', path: {'name': 'Notifications'}},
      {title: notifications.current.data.title}
    ]"
  >
    <XBox>
      <div
        class="show-space"
        v-html="notificationsContent"
      />
    </XBox>
  </XPage>
</template>

<script>

import _cond from 'lodash/cond';
import _stubTrue from 'lodash/stubTrue';
import _get from 'lodash/get';
import { mapState, mapActions } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XBox from '../axons/layout/Box.vue';

import { FETCH_NOTIFICATION, UPDATE_NOTIFICATIONS_SEEN } from '../../store/modules/notifications';
import { NotificationHookTypeEnum, NotificationHookHtmlTagEnum } from '../../constants/notifications';

export default {
  name: 'XNotification',
  components: { XPage, XBox },
  computed: {
    ...mapState({
      notifications(state) {
        return state.notifications;
      },
      isReadOnly(state) {
        const user = _get(state, 'auth.currentUser.data');
        if (!user || !user.permissions) return true;
        return user.permissions.Dashboard === 'ReadOnly';
      },
    }),
    notificationId() {
      return this.$route.params.id;
    },
    notificationData() {
      return this.notifications.current.data;
    },
    notificationsContent() {
      const hookHandler = _cond([
        [this.isLinkHook, this.linkHookHandler],
        [_stubTrue, ({ notificationContent }) => notificationContent],
      ]);

      let notificationContent = this.notificationData.content;
      if (this.notificationData.hooks) {
        this.notificationData.hooks.forEach((hookItem) => {
          notificationContent = hookHandler({ notificationContent, hookItem });
        });
      }
      return notificationContent;
    },
  },
  watch: {
    notificationData(newNotificationData) {
      if (!newNotificationData.seen && !this.isReadOnly) {
        this.updateNotificationsSeen([this.notificationId]);
      }
    },
  },
  methods: {
    ...mapActions(
      {
        fetchNotification: FETCH_NOTIFICATION,
        updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN,
      },
    ),
    isLinkHook({ hookItem }) {
      return hookItem.type === NotificationHookTypeEnum.link;
    },
    linkHookHandler({ notificationContent, hookItem }) {
      return notificationContent.replace(
        new RegExp(`{${hookItem.key}}`, 'g'),
        `<${NotificationHookHtmlTagEnum.link} href="${hookItem.value}">${
          hookItem.value
        }</${NotificationHookHtmlTagEnum.link}>`,
      );
    },
  },
  mounted() {
    /*
      Refresh or navigation directly to the url,
      will cause missing or incorrect notifications controls.
      This condition should identify the situation and re-fetch the notifications
    */
    if (!this.notificationData || !this.notificationData.uuid
              || (this.notificationData.uuid !== this.notificationId)) {
      this.fetchNotification(this.notificationId);
    } else if (!this.notificationData.seen && !this.isReadOnly) {
      this.updateNotificationsSeen([this.notificationId]);
    }
  },
};
</script>

<style lang="scss">

</style>
