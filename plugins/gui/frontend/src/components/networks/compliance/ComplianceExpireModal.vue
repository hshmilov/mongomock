<template>
  <AModal
    id="x-compliance-expire-modal"
    :mask-style="{left: modelCollapsePosition}"
    :visible="true"
    :cancel-button-props="{ props: { type: 'link' } }"
    :closable="false"
    :width="null"
    :centered="true"
    :wrap-class-name="collapseSidebar ? 'modal-wrap-collapse' : 'modal-wrap-uncollapse'"
  >
    <div class="content">
      <XIcon
        class="compliance-icon"
        family="navigation"
        type="compliance"
      />
      <div class="compliance-tip-title">
        <span>Your
          <XButton
            type="link"
            class="cis-link"
            @click="openCISLink"
          >Cloud Asset Compliance Center</XButton>
          trial has expired. <br>
          Contact your Axonius sales representative.
        </span>
      </div>
    </div>

    <template slot="footer">
      <div />
    </template>
  </AModal>
</template>

<script>
import { mapState } from 'vuex';

import { mdiArrowRight } from '@mdi/js';
import { Modal } from 'ant-design-vue';

export default {
  name: 'XComplianceExpireModal',
  components: {
    AModal: Modal,
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
  },
  mounted() {
    if (this.collapseSidebar) {
      this.modalStyle.left = '60px';
    } else {
      this.modalStyle.left = '240px';
    }
  },
  methods: {
    openCISLink() {
      window.open('https://www.axonius.com/platform/cloud-asset-compliance/');
    },
  },
};
</script>

<style lang="scss">

  #x-compliance-expire-modal {
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
                    .compliance-tip-title {
                        margin-top: 15px;
                        margin-bottom: 30px;
                        line-height: 21px;
                        font-size: 17px;
                        font-weight: 300;

                        .cis-link {
                            color: $theme-orange;
                            padding: 0;
                            font-size: 17px;
                        }
                    }
                    .compliance-icon {
                        svg {
                            fill: $theme-white;
                            stroke: $theme-orange;
                        }
                        font-size: 90px;
                    }
                }
            }
            .ant-modal-footer {
                height: 50px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
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
