<template>
  <Transition
    name="grow-shrink"
    appear
    enter-active-class="growing-y"
    leave-to-class="shrinking-y"
  >
    <XTabs v-if="data">
      <XTab
        v-for="(settings, configName, i) in data"
        :id="configName"
        :key="i"
        :title="settings.schema.pretty_name || configName"
        :selected="!i"
        class="advanced-settings-tab"
      >
        <div class="configuration">
          <XForm
            v-model="settings.config"
            :schema="settings.schema"
            @validate="validateConfig"
          />
          <XButton
            type="primary"
            tabindex="1"
            :disabled="!configValid"
            @click="saveConfig(configName, settings.config)"
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
  .advanced-settings-tab {
    overflow: hidden;
    width: 60vw;

    .configuration {
      width: calc(60vw - 72px);
      padding: 24px;
    }
  }
</style>
