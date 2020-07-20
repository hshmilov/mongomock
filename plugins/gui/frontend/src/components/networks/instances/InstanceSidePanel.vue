<template>
  <XSidePanel
    :visible="visible"
    :panel-container="getSidePanelContainer"
    panel-class="x-instance-side-panel"
    :title="sidePanelTitle"
    @close="onClose"
  >
    <div
      slot="panelContent"
      class="body"
    >
      <div class="content">
        <div class="editable-input">
          <div class="editable-input__instance-field">
            <h5>Instance Name</h5>
            <AInput
              id="node_name"
              v-model="instance.node_name"
              :disabled="disabled"
              @change="$emit('update:instance', instance)"
            />
          </div>
          <div class="editable-input__instance-field">
            <h5>Show Indication</h5>
            <ACheckbox
              v-model="instance.use_as_environment_name"
              :disabled="disabled"
              @change="$emit('update:instance', instance)"
            />
          </div>
          <div class="editable-input__instance-field">
            <h5>Host Name</h5>
            <AInput
              id="hostname"
              v-model="instance.hostname"
              :disabled="disabled"
              @change="$emit('update:instance', instance)"
            />
          </div>
        </div>

        <div class="readonly-instance-fields">
          <div class="readonly-instance-fields__instance-field">
            <h5 class="readonly-title">
              IP
            </h5>
            <p>{{ instance.ips ? instance.ips.join(', ') : '' }}</p>
          </div>
          <div class="readonly-instance-fields__instance-field">
            <h5 class="readonly-title">
              Last Seen
            </h5>
            <p>{{ instance.last_seen }}</p>
          </div>
          <div class="readonly-instance-fields__instance-field">
            <h5 class="readonly-title">
              Status
            </h5>
            <p>{{ instance.status }}</p>
          </div>
        </div>

        <ADivider
          class="separator"
          type="horizontal"
        />

        <div class="instance-metrics">
          <h5 class="metrics-title">
            Performance Metrics
          </h5>
          <p>
            Last updated: {{ lastUpdated }}
          </p>
          <div
            v-for="field in metricsFields"
            :key="field.name"
            class="instance-metric-field"
          >
            <div
              v-if="instance[field.name]"
              class="field-container"
            >
              <label class="field-title readonly-title-metrics"> {{ getTitle(field.type, field.name, field.title, instance[field.name]) }} </label>
              <p
                class="field-value"
              >
                {{ getFieldValue(field.type, instance[field.name]) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
    <template
      slot="panelFooter"
    >
      <XButton
        v-if="showActivationOption === 'Activated'"
        :disabled="disabled"
        class="activation"
        type="link"
        @click="$emit('deactivate')"
      >Deactivate
      </XButton>
      <XButton
        v-if="showActivationOption === 'Deactivated'"
        :disabled="disabled"
        class="activation"
        type="link"
        @click="$emit('reactivate')"
      >Reactivate
      </XButton>
      <div />
      <XButton
        :disabled="disabled"
        type="primary"
        @click="$emit('save')"
      >Save
      </XButton>
    </template>
  </XSidePanel>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import {
  Checkbox, Divider, Input,
} from 'ant-design-vue';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import XButton from '@axons/inputs/Button.vue';
import { formatDate } from '@constants/utils';

export default {
  name: 'XInstanceSidePanel',
  components: {
    XSidePanel,
    AInput: Input,
    ACheckbox: Checkbox,
    ADivider: Divider,
    XButton,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    instance: {
      type: Object,
      default: () => {
      },
    },
    disabled: {
      type: Boolean,
    },
  },
  computed: {
    ...mapState({
      retention(state) {
        return _get(state.settings,
          'configurable.system_scheduler.SystemSchedulerService.config.discovery_settings.history_settings',
          {});
      },
    }),
    sidePanelTitle() {
      return this.instance.node_name;
    },
    showActivationOption() {
      return this.instance.status;
    },
    metricsFields() {
      return [
        {
          name: 'cpu_usage', title: 'CPU Usage', type: 'percentage',
        },
        {
          name: 'data_disk_free_space', title: 'Hard Drive(Data): Free Size ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'data_disk_size', title: 'Hard Drive(Data): Size ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'os_disk_free_space', title: 'Hard Drive(OS): Free Size ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'os_disk_size', title: 'Hard Drive(OS): Size ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'memory_free_space', title: 'Free RAM ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'memory_size', title: 'Total RAM ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'swap_free_space', title: 'Free Swap ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'swap_size', title: 'Total Swap ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'swap_cache_size', title: 'Cached Swap ({SIZE_POSTIFX})', type: 'size',
        },
        {
          name: 'physical_cpu', title: 'Total Physical Processors', type: 'string',
        },
        {
          name: 'cpu_cores', title: 'CPUs: Cores', type: 'string',
        },
        {
          name: 'cpu_core_threads', title: 'CPUs: Threads in core', type: 'string',
        },
        {
          name: 'last_snapshot_size', title: 'Last Historical Snapshot ({SIZE_POSTIFX})', type: 'size',
        },
        // AX-8502
        // {
        //   name: 'max_snapshots', title: 'Maximum Historical Snapshots', type: 'string',
        // },
        {
          name: 'remaining_snapshots_days', title: 'Historical snapshots days remaining', type: 'string',
        },
      ];
    },
    lastUpdated() {
      return formatDate(this.instance.last_updated);
    },
  },
  methods: {
    onClose() {
      this.$emit('close');
    },
    getSidePanelContainer() {
      return document.querySelector('.x-table');
    },
    getFieldValue(type, value) {
      if (type === 'size') {
        return this.getDynamicSize(value);
      }
      if (type === 'percentage') {
        return `${value}%`;
      }
      return value;
    },
    getDynamicSize(sizeInKb) {
      const sizeInMb = parseInt(sizeInKb, 10) / 1024;
      if (sizeInMb < 1024) {
        return sizeInMb.toFixed(1);
      }
      return (sizeInMb / 1024).toFixed(1);
    },
    getTitle(type, key, title, value) {
      if (type === 'size') {
        const postfixTitle = title.replace('{SIZE_POSTIFX}', this.getSizePostfix(value));
        if (key === 'data_disk_free_space' || key === 'data_disk_size') {
          // If data disk is the only disk, no need to to split the titles, and display only only one disk.
          if (value && !this.instance.os_disk_size) {
            return postfixTitle.replace('(Data)', '');
          }
        }
        return postfixTitle;
      }
      return title;
    },
    getSizePostfix(sizeInKb) {
      const sizeInMb = parseInt(sizeInKb, 10) / 1024;
      if (sizeInMb < 1024) {
        return 'MB';
      }
      return 'GB';
    },
  },
};
</script>

<style lang="scss">
  .x-instance-side-panel {

    .ant-drawer-content-wrapper {
      .ant-drawer-wrapper-body  {
        .ant-drawer-body__content {
          padding: 5px 28px 5px 5px;
        }
      }
    }

    .ant-drawer-body {

      .separator {
        margin: 10px 0px 15px 0px;
      }

      .readonly-title {
        font-weight: 400;
      }

      .editable-input {
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-template-rows: 1fr 1fr;

        &__instance-field {
          display: flex;
          flex-direction: column;
          padding: 10px 25px 10px 0px;
        }
      }

      .readonly-instance-fields {

        &__instance-field {
          display: flex;
          flex-direction: column;
          padding: 10px 25px 10px 0px;
          height: 50px;
        }

      }

      .instance-metrics {
        display: flex;
        flex-direction: column;
        padding-bottom: 30px;

        .metrics-title {
          margin-bottom: 8px;
        }

        .instance-metric-field {
          .field-container {
            display: flex;
            flex-direction: row;

            .field-title {
              width: 250px;
              margin: 0px 10px 10px 0px
            }

            .readonly-title-metrics {
              font-weight: 300;
            }
          }
        }
      }

      &__footer {
        display: grid;
        padding: 20px;
        grid-template-columns: 150px auto 150px;


        .activation {
          padding-left: 0px;
          width: fit-content;
        }

      }
    }
  }

</style>
