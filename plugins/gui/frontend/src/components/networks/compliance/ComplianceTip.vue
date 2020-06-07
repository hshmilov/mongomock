<template>
  <XModal
    size="s"
    class="x-compliance-tip"
    @close="$emit('close')"
  >
    <div
      slot="body"
      class="body"
    >
      <div class="content">
        <XIcon
          class="compliance-icon"
          family="navigation"
          type="compliance"
        />
        <div class="compliance-title">
          <span>Ready to see how your cloud assets comply with standards and benchmarks?</span>
        </div>
        <div class="compliance-note">
          <span>The new
            <XButton
              type="link"
              class="cis-link"
              @click="openCISLink"
            >Cloud Asset Compliance Center</XButton>
            shows how cloud instances and accounts adhere to compliance standards
          </span>
        </div>
      </div>
    </div>
    <div slot="footer">
      <XButton
        type="link"
        @click="openMail"
      >Upgrade<XIcon type="arrow-right" />
      </XButton>
    </div>
  </XModal>
</template>

<script>
import XIcon from '@axons/icons/Icon';
import XModal from '../../axons/popover/Modal/index.vue';
import XButton from '../../axons/inputs/Button.vue';

export default {
  name: 'XComplianceTip',
  components: {
    XModal, XButton, XIcon,
  },
  props: {
    enabled: {
      type: Boolean,
      default: true,
    },
  },
  methods: {
    openMail() {
      const subject = 'I\'d like to try Cloud Asset Compliance for AWS';
      const body = 'I\'d like to try the Cloud Asset Compliance for AWS feature in Axonius. '
        + 'Please enable that for me, and let me know how to get started!';
      window.open(`mailto:sales@axonius.com?subject=${subject}&body=${body}`);
    },
    openCISLink() {
      window.open('https://www.axonius.com/platform/cloud-asset-compliance-AWS');
    },
  },
};
</script>

<style lang="scss">
  .x-compliance-tip {
    &.x-modal {
      position: absolute;
      .modal-container {
        padding: unset;
        border-radius: 10px;
        .modal-body {
          padding: 24px;
        }
        .modal-footer {
          text-align: center;
          line-height: 60px;
          border-bottom-left-radius: 10px;
          border-bottom-right-radius: 10px;
          .ant-btn-link {
            color: $theme-white;
          }
          background-color: $theme-orange;
        }
      }
      .modal-overlay {
        position: absolute;
      }
    }
    .body {
      display: flex;
      flex-direction: column;
      justify-content: center;

      .content {
        .x-icon {
          font-size: 48px;
          svg {
            fill: $theme-white;
            stroke: $theme-orange;
          }
        }
        text-align: center;
        margin-top: 12px;
        width: 380px;

        .compliance-title {
          margin-top: 30px;
          line-height: 21px;
          font-size: 18px;
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
      }

    }
  }
</style>
