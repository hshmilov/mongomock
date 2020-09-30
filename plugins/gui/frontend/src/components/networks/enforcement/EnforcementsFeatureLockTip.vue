<template>
  <AModal
    id="enforcement_feature_lock"
    :mask-style="{left: modelCollapsePosition}"
    :visible="enabled"
    class="x-enforcements-feature-lock-tip"
    :cancel-button-props="{ props: { type: 'link' } }"
    :closable="false"
    :width="null"
    :centered="true"
    :wrap-class-name="collapseSidebar ? 'modal-wrap-collapse' : 'modal-wrap-uncollapse'"
    @cancel="onCancel"
  >
    <div class="content">
      <VIcon
        class="enforcements-lock"
      >$vuetify.icons.enforcementsLock</VIcon>
      <div class="compliance-title">
        <span>Ready to run actions on your assets?</span>
      </div>
      <div class="compliance-note">
        <span>The
          <XButton
            type="link"
            class="cis-link"
            @click="openCISLink"
          >Enforcement Center</XButton>
          allows you to notify teams, enrich data <br>
          and manage assets that do not adhere to your security policy
        </span>
      </div>
    </div>

    <template slot="footer">
      <XButton
        type="link"
        @click="openMail"
      >Upgrade<VIcon
        size="20px"
        color="white"
      >{{ arrowIcon }}</VIcon>
      </XButton>
    </template>
  </AModal>
</template>

<script>
import { mapState } from 'vuex';

import { mdiArrowRight } from '@mdi/js';
import { Modal } from 'ant-design-vue';

export default {
  name: 'XEnforcementsFeatureLockTip',
  components: {
    AModal: Modal,
  },
  props: {
    enabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      modalStyle: { left: 0 },
    };
  },
  computed: {
    ...mapState({
      collapseSidebar(state) {
        return state.interaction.collapseSidebar;
      },
    }),
    modelCollapsePosition() {
      return this.collapseSidebar ? '60px' : '240px';
    },
    arrowIcon() {
      return mdiArrowRight;
    },
  },
  mounted() {
    if (this.collapseSidebar) {
      this.modalStyle.left = '60px';
    } else {
      this.modalStyle.left = '240px';
    }
  },
  methods: {
    openMail() {
      const subject = 'I\'d like to try Enforcement Center';
      const body = 'I\'d like to try the Enforcement Center feature in Axonius.'
          + 'Please enable that for me, and let me know how to get started!;';
      window.open(`mailto:sales@axonius.com?subject=${subject}&body=${body}`);
    },
    openCISLink() {
      window.open('https://docs.axonius.com/docs/enforcement-center-overview');
    },
    onCancel() {
      this.$emit('close-lock-tip');
    },
  },
};
</script>

<style lang="scss">
      #enforcement_feature_lock {
        .ant-modal-content {
          padding: unset;
          border-radius: 10px;
          .ant-modal-body {
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            .content {
              text-align: center;
              margin-top: 12px;
              width: 420px;
              .compliance-title {
                margin-top: 30px;
                line-height: 21px;
                font-size: 18px;
                font-weight: 300;
              }
              .compliance-note {
                margin-top: 30px;
                font-size: 14px;
                line-height: 16px;
                .cis-link {
                  color: $theme-orange;
                  padding: 0;
                }
              }
                .enforcements-lock {
                    svg {
                        fill: $theme-white;
                    }
                    height: 90px;
                    width: 90px;
                }
            }
          }
          .ant-modal-footer {
            padding-top: 10px;
            padding-bottom: 10px;
            text-align: center;
            line-height: 15px;
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            .ant-btn-link {
              color: $theme-white;
              svg {
                fill: $theme-white;
              }
            }
            background-color: $theme-orange;
          }
        }
        .modal-wrap-collapse {
          left: 60px;
        }
        .modal-wrap-uncollapse {
          left: 240px;
        }
      }
</style>
