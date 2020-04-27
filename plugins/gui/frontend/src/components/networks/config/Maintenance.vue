<template>
  <MdCard class="x-maintenance">
    <MdCardExpand>
      <MdCardExpandTrigger>
        <XButton
          id="maintenance_settings"
          class="x-button"
          type="link"
          :disabled="readOnly"
        >
          ADVANCED SETTINGS
        </XButton>
      </MdCardExpandTrigger>
      <MdCardExpandContent>
        <MdCardContent>
          <XCheckbox
            ref="provision"
            v-model="allowProvision"
            label="Remote Support"
          />
          <div
            v-if="allowProvision"
            class="x-content"
          >
            <div class="x-section">
              <XCheckbox
                ref="analytics"
                v-model="allowAnalytics"
                label="Anonymized Analytics"
              />
              <div v-if="allowAnalytics">
                <div class="message-title">
                  Warning:
                </div>
                <div class="content">
                  {{ disableWarnings['analytics'] }}
                </div>
              </div>
              <div
                v-else
                class="message-title"
              >Turning on this feature allows Axonius to proactively detect
                issues and notify about errors
              </div>
            </div>
            <div class="x-section">
              <XCheckbox
                ref="troubleshooting"
                v-model="allowTroubleshooting"
                label="Remote Access"
              />
              <div v-if="allowTroubleshooting">
                <div class="message-title">
                  Warning:
                </div>
                <div class="content">
                  {{ disableWarnings['troubleshooting'] }}
                </div>
              </div>
              <div
                v-else
                class="message-title"
              >Turning on this feature allows Axonius to keep the system updated
                and speed-up issues resolution time
              </div>
            </div>
          </div>
          <div
            v-else
            class="x-content"
          >
            <div class="x-section message-title">Turning on this feature allows Axonius to keep the system updated,
              speed-up issues resolution time and proactively detect issues and notify about errors
            </div>
            <div class="x-section">
              <div class="message-title">
                OR
              </div>
              <div class="config">
                <template v-if="accessEndTime">
                  <div class="warning mr-12">
                    Temporary Remote Support will end at: {{ accessEndTime }}
                  </div>
                  <XButton
                    type="primary"
                    @click="stopTempAccess"
                  >
                    Stop
                  </XButton>
                </template>
                <template v-else>
                  <div class="mr-8">
                    Give temporary Remote Support for
                  </div>
                  <input
                    id="remote-access-timer"
                    v-model="accessDuration"
                    type="number"
                    class="mr-8"
                    @keypress="validateNumber"
                  >
                  <div class="mr-12">
                    Hours
                  </div>
                  <XButton
                    :disabled="!enableStartAccess"
                    @click="startTempAccess"
                  >
                    Start
                  </XButton>
                </template>
              </div>
            </div>
          </div>
        </MdCardContent>
      </MdCardExpandContent>
    </MdCardExpand>
    <XModal
      v-if="disableToConfirm"
      approve-text="Confirm"
      @confirm="approveDisable"
      @close="cancelDisable"
    >
      <div slot="body">
        <div>
          <div class="message-title">
            Warning:
          </div>
          <div class="content">
            {{ disableWarnings[disableToConfirm] }}
          </div>
        </div>
        <div class="mt-12">
          Turn off this feature?
        </div>
      </div>
    </XModal>
  </MdCard>
</template>

<script>
import { mapState, mapActions, mapGetters } from 'vuex';
import { formatDate } from '@constants/utils';
import { DATE_FORMAT } from '../../../store/getters';
import XCheckbox from '../../axons/inputs/Checkbox.vue';
import XButton from '../../axons/inputs/Button.vue';
import XModal from '../../axons/popover/Modal/index.vue';

import {
  FETCH_MAINTENANCE_CONFIG, SAVE_MAINTENANCE_CONFIG, START_MAINTENANCE_CONFIG, STOP_MAINTENANCE_CONFIG,
} from '../../../store/modules/settings';

import { validateNumber } from '../../../constants/validations';

export default {
  name: 'XMaintenance',
  components: { XCheckbox, XButton, XModal },
  props: {
    readOnly: {
      type: Boolean, default: false,
    },
  },
  computed: {
    ...mapState({
      maintenance(state) {
        return state.settings.advanced.maintenance;
      },
    }),
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    allowProvision: {
      get() {
        return this.maintenance.provision;
      },
      set(value) {
        this.onMaintenanceChange('provision', value);
      },
    },
    allowAnalytics: {
      get() {
        return this.maintenance.analytics;
      },
      set(value) {
        this.onMaintenanceChange('analytics', value);
      },
    },
    allowTroubleshooting: {
      get() {
        return this.maintenance.troubleshooting;
      },
      set(value) {
        this.onMaintenanceChange('troubleshooting', value);
      },
    },
    accessEndTime() {
      if (!this.maintenance.timeout) return null;
      return formatDate(this.maintenance.timeout, undefined, this.dateFormat);
    },
    disableWarnings() {
      return {
        analytics: 'Turning off this feature prevents Axonius from proactively detecting issues and notifying about errors',
        troubleshooting: 'Turning off this feature prevents Axonius from updating the system and can lead to slower issue resolution time',
        provision: 'Turning off this feature prevents Axonius from any remote support, including Anonymized Analytics and Remote Access',
      };
    },
    enableStartAccess() {
      return this.accessDuration > 0 && this.accessDuration < 100000000;
    },
  },
  data() {
    return {
      accessDuration: 24,
      disableToConfirm: null,
    };
  },
  methods: {
    ...mapActions({
      saveMaintenance: SAVE_MAINTENANCE_CONFIG,
      fetchMaintenance: FETCH_MAINTENANCE_CONFIG,
      startMaintenance: START_MAINTENANCE_CONFIG,
      stopMaintenance: STOP_MAINTENANCE_CONFIG,
    }),
    onMaintenanceChange(type, value) {
      if (value === this.maintenance[type]) return;
      if (value) {
        this.saveMaintenance({ [type]: value });
      } else {
        this.disableToConfirm = type;
      }
    },
    approveDisable() {
      this.saveMaintenance({ [this.disableToConfirm]: false });
      this.disableToConfirm = null;
    },
    cancelDisable() {
      this.$refs[this.disableToConfirm].$el.click();
      this.disableToConfirm = null;
    },
    validateNumber,
    startTempAccess() {
      this.startMaintenance({ duration: this.accessDuration });
    },
    stopTempAccess() {
      this.stopMaintenance();
    },
  },
  created() {
    this.fetchMaintenance();
  },
};
</script>

<style lang="scss">
    .x-maintenance.md-card {
        box-shadow: none;

        .md-card-expand {
            min-height: 36px;
        }

        .md-card-content {
            min-height: 240px;
        }

        .message-title {
            font-weight: 400;
            display: inline-block;
        }

        .content {
            margin-left: 4px;
            display: inline;
        }

        .config {
            display: flex;
            align-items: center;
        }

        .warning {
            font-style: italic;
        }
    }

    #maintenance_settings {
        z-index: 10;
    }
</style>
