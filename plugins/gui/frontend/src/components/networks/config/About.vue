<template>
  <div class="x-settings-about">
    <XArrayView
      :schema="schema"
      :value="systemInfo"
    />
    <label v-if="newVersionAvailable">
      <a href="mailto:support@axonius.com?subject=Request for upgrade">Contact us</a>
      to request an update.
    </label>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import { DATE_FORMAT } from '@store/getters';
import { REQUEST_API } from '@store/actions';

import XArrayView from '../../neurons/schema/types/array/ArrayView.vue';

const METADATA_EXPIRY_DATE_KEY = {
  name: 'Contract Expiry Date',
  title: 'Contract Expiry Date',
  type: 'string',
  format: 'date',
};

const METADATA_LATEST_VERSION_KEY = {
  name: 'Latest Available Version',
  title: 'Latest Available Version',
  type: 'string',
  format: 'string',
};

const METADATA_INSTALLED_VERSION_KEY = {
  name: 'Installed Version',
  title: 'Installed Version',
  type: 'string',
};

const METADATA_CUSTOMER_ID_KEY = {
  name: 'Customer ID',
  title: 'Customer ID',
  type: 'string',
};

const METADATA_BUILD_DATE_KEY = {
  name: 'Build Date',
  title: 'Build Date',
  type: 'string',
  format: 'date',
};

export default {
  name: 'XAbout',
  components: { XArrayView },
  data() {
    return {
      systemInfo: null,
    };
  },
  computed: {
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    schema() {
      return {
        type: 'array',
        items: [
          METADATA_BUILD_DATE_KEY,
          METADATA_CUSTOMER_ID_KEY,
          METADATA_EXPIRY_DATE_KEY,
          METADATA_INSTALLED_VERSION_KEY,
          METADATA_LATEST_VERSION_KEY,
        ],
      };
    },
    newVersionAvailable() {
      return this.systemInfo && METADATA_LATEST_VERSION_KEY.name in this.systemInfo;
    },
  },
  async created() {
    const response = await this.fetchData({
      rule: 'settings/metadata',
    });
    this.systemInfo = response.data;
  },
  methods: {
    ...mapActions({
      fetchData: REQUEST_API,
    }),
  },
};
</script>

<style lang="scss">
  .x-settings-about {
    .array.ordered .item-container {
      padding-bottom: 12px;
    }
  }
</style>
