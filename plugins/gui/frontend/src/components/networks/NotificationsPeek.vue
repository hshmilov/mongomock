<template>
  <XDropdown
    ref="notifications"
    size="lg"
    align="right"
    :align-space="-4"
    :arrow="false"
    class="x-notification-peek"
    @click.native="clearNotifications"
  >
    <div slot="trigger">
      <SvgIcon
        name="navigation/notifications"
        :original="true"
        height="20"
      />
      <div
        v-if="notificationUnseenCount"
        class="notification-badge"
      >
        {{ notificationUnseenCount }}
      </div>
    </div>
    <div slot="content">
      <h5 class="mb-8">
        Notifications
      </h5>
      <div
        v-for="notification in notificationAggregatedList"
        :key="notification.uuid"
        class="notification"
        :class="{ bold: !notification.seen }"
        @click="navigateNotification(notification.uuid)"
      >
        <div class="status">
          <SvgIcon
            :name="`symbol/${notification.severity}`"
            :original="true"
            height="16"
          />
        </div>
        <div class="content">
          <div class="d-flex">
            <div class="notification-title">
              {{ notification.title }}
            </div>
            <div
              v-if="notification.count"
              class="c-grey-3"
            >
              ({{ notification.count }})
            </div>
          </div>
          <div class="c-grey-4">
            {{ relativeDate(notification.date_fetched) }}
          </div>
        </div>
        <div><!-- Place for Delete --></div>
      </div>
      <div
        v-if="!notificationAggregatedList.length"
        class="t-center"
      >
        <SvgIcon
          name="symbol/success"
          :original="true"
          height="20px"
        />
      </div>
      <XButton
        type="link"
        @click="navigateNotifications"
      >
        View All
      </XButton>
    </div>
  </XDropdown>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import XButton from '../axons/inputs/Button.vue';
import XDropdown from '../axons/popover/Dropdown.vue';

import {
  FETCH_NOTIFICATIONS_UNSEEN_COUNT,
  FETCH_AGGREGATE_NOTIFICATIONS,
  UPDATE_NOTIFICATIONS_SEEN,
  FETCH_NOTIFICATION,
} from '../../store/modules/notifications';

export default {
  name: 'XNotificationPeek',
  components: { XButton, XDropdown },
  computed: {
    ...mapState({
      notificationUnseenCount(state) {
        return state.notifications.unseenCount.data;
      },
      notificationAggregatedList(state) {
        return state.notifications.aggregatedList.data;
      },
    }),
    canResetNotifications() {
      return this.$can(this.$permissionConsts.categories.Dashboard,
        this.$permissionConsts.actions.View);
    },
  },
  created() {
    const loadNotifications = () => {
      Promise.all([this.fetchAggregateNotifications(), this.fetchNotificationsUnseenCount({})])
        .then(() => {
          // eslint-disable-next-line no-underscore-dangle
          if (this._isDestroyed) return;
          this.timer = setTimeout(loadNotifications, 9000);
        });
    };
    loadNotifications();
  },
  beforeDestroy() {
    clearTimeout(this.timer);
  },
  methods: {
    ...mapActions({
      fetchNotification: FETCH_NOTIFICATION,
      fetchAggregateNotifications: FETCH_AGGREGATE_NOTIFICATIONS,
      updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN,
      fetchNotificationsUnseenCount: FETCH_NOTIFICATIONS_UNSEEN_COUNT,
    }),
    relativeDate(timestamp) {
      const date = new Date(timestamp);
      const now = Date.now();
      if (now - date.getTime() < 24 * 60 * 60 * 1000) {
        return date.toLocaleTimeString();
      } if (now - date.getTime() < 48 * 60 * 60 * 1000) {
        return 'Yesterday';
      }
      return date.toLocaleDateString();
    },
    navigateNotification(notificationId) {
      this.fetchNotification(notificationId);
      this.$refs.notifications.close();
      this.$router.push({ path: `/notifications/${notificationId}` });
    },
    clearNotifications() {
      if (!this.canResetNotifications) return;
      this.updateNotificationsSeen([]);
    },
    navigateNotifications() {
      this.$refs.notifications.close();
      this.$router.push({ name: 'Notifications' });
    },
  },
};
</script>

<style lang="scss">
    .x-notification-peek {
        &.x-dropdown > .content {
            background-color: $grey-1;

            &:before {
                content: '';
                position: absolute;
                height: 6px;
                width: 6px;
                top: -3px;
                right: 12px;
                box-shadow: $popup-shadow;
                transform: rotate(45deg);
                background-color: $grey-1;
            }

            &:after {
                content: '';
                position: absolute;
                height: 8px;
                width: 12px;
                top: 0;
                right: 10px;
                background-color: $grey-1;
            }
        }

        .notification {
            background-color: $theme-white;
            display: grid;
            grid-template-columns: 40px auto 40px;
            margin: 2px -12px;
            letter-spacing: 1px;
            padding: 12px 0;

            &.bold {
                font-weight: 500;
            }

            .status {
                line-height: 30px;
                text-align: center;
            }

            .content {
                text-overflow: ellipsis;
                overflow: hidden;
                font-size: 12px;
                line-height: 16px;

                .notification-title {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    margin-right: 4px;
                }
            }

            &:hover {
                box-shadow: 0 0 12px rgba(0, 0, 0, 0.1)
            }
        }

        .x-button {
            text-align: right;
            margin-bottom: -8px;
        }
    }

</style>
