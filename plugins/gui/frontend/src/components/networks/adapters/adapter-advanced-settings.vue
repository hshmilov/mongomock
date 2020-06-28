<template>
  <Transition
    name="grow-shrink"
    appear
    enter-active-class="growing-y"
    leave-to-class="shrinking-y"
  >
    <XTabs v-if="data">
      <XTab
        v-for="(dataObj, i) in sortedData"
        :id="dataObj.name"
        :key="i"
        :title="dataObj.settings.schema.pretty_name || dataObj.name"
        :selected="!i"
        class="advanced-settings-tab"
      >
        <div class="configuration">
          <XForm
            v-model="dataObj.settings.config"
            :schema="dataObj.settings.schema"
            @validate="validateConfig"
          />
          <XButton
            type="primary"
            tabindex="1"
            :disabled="!configValid"
            @click="saveConfig(dataObj.name, dataObj.settings.config)"
          >Save Config</XButton>
        </div>
      </XTab>
    </XTabs>
  </Transition>
</template>

<script>
import XTabs from '@axons/tabs/Tabs.vue';
import XTab from '@axons/tabs/Tab.vue';
import XButton from '@axons/inputs/Button.vue';
import XForm from '@neurons/schema/Form.vue';

import { fetchAdapterAdvancedSettings } from '@api/adapters';

export default {
  name: 'XAdapterAdvancedSettings',
  components: {
    XTabs,
    XTab,
    XButton,
    XForm,
  },
  props: {
    adapterUniqueName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      configValid: true,
      data: null,
    };
  },
  computed: {
    sortedData() {
      const discoveryLast = (a, b) => {
        if (a !== 'DiscoverySchema' && b !== 'DiscoverySchema') {
          return 0;
        }
        return a === 'DiscoverySchema' ? 1 : -1;
      };
      return Object.keys(this.data).sort(discoveryLast).map((name) => ({
        name, settings: this.data[name],
      }));
    },
  },
  async created() {
    const res = await fetchAdapterAdvancedSettings(this.adapterUniqueName);
    this.data = res;
  },
  methods: {
    validateConfig(valid) {
      this.configValid = valid;
    },
    saveConfig(configName, config) {
      this.$emit('save', { configName, config });
    },
  },
};
</script>

<style lang="scss">
  div[role="menu"] {
    min-width: auto !important;
  }
  .advanced-settings-tab {
    overflow: hidden;
    width: 60vw;

    .configuration {
      width: calc(60vw - 72px);
      padding: 24px;
    }
  }
  .DiscoverySchema {
    .configuration > .x-form > .x-array-edit .list {
      grid-template-columns: 1fr;
    }
    .x-array-edit {
      .time-picker-text, .x-dropdown, input {
        display: inline-block;
        width: 200px;
      }
      .v-text-field {
        padding-top: 0;
      }
    }
   .v-text-field__details, .v-messages {
      min-height: 0;
    }
    #repeat_on {
      display: none;
    }
    span.server-time {
      padding-left: 15px;
    }
    label {
      display: block;
    }
  }


</style>
