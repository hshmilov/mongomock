<template>
  <AModal
    id="csv_export_config"
    :visible="true"
    title="Export Data"
    :cancel-button-props="{ props: { type: 'link' } }"
    :closable="false"
    :centered="true"
    :after-close="resetForm"
    @cancel="onCancel"
  >
    <div
      ref="wrapper_div"
      class="form_container"
      :tabindex="-1"
      @keyup.enter.stop.prevent="submitFormOnEnter"
    >
      <AForm>
        <AFormItem
          class="w-sm"
          :colon="false"
        >
          <span slot="label">
            Delimiter to use for multi-value fields
            <div class="hint">optional</div>
          </span>
          <AInput
            id="csv_delimiter"
            v-model="delimiter"
          />
        </AFormItem>
        <AFormItem
          class="w-sm"
          :colon="false"
        >
          <span slot="label">
            Maximum rows
            <div class="hint">optional</div>
          </span>
          <AInputNumber
            id="csv_max_rows"
            v-model="maxRows"
            class="input-number"
            :min="1"
            :max="defaultMaxRows"
          />
        </AFormItem>
      </AForm>
    </div>
    <template slot="footer">
      <XButton
        type="link"
        @click="onCancel"
      >
        Cancel
      </XButton>
      <XButton
        type="primary"
        @click="onExport"
      >
        Export
      </XButton>
    </template>
  </AModal>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import {
  Modal, Form, Input, InputNumber,
} from 'ant-design-vue';

export default {
  name: 'XCsvExportConfig',
  components: {
    AModal: Modal,
    AForm: Form,
    AFormItem: Form.Item,
    AInputNumber: InputNumber,
    AInput: Input,
  },
  data() {
    return {
      form: {
        delimiter: null,
        maxRows: 0,
      },
    };
  },
  computed: {
    ...mapState({
      defaultDelimiter(state) {
        return _get(state, 'configuration.data.system.cell_joiner')
          || _get(state, 'constants.constants.csv_configs.cell_joiner', '').replace(/'/g, '');
      },
      defaultMaxRows(state) {
        return _get(state, 'constants.constants.csv_configs.max_rows', null);
      },
    }),
    delimiter: {
      get() {
        return this.form.delimiter === null ? this.defaultDelimiter : this.form.delimiter;
      },
      set(value) {
        this.form.delimiter = value;
      },
    },
    maxRows: {
      get() {
        return this.form.maxRows === 0 ? this.defaultMaxRows : this.form.maxRows;
      },
      set(value) {
        this.form.maxRows = value;
      },
    },
  },
  mounted() {
    this.$refs.wrapper_div.focus();
  },
  methods: {
    onExport() {
      this.$emit('run-csv-export-config', this.delimiter, this.maxRows);
    },
    onCancel() {
      this.$emit('close-csv-export-config');
    },
    resetForm() {
      this.form = {
        delimiter: null,
        maxRows: 0,
      };
    },
    submitFormOnEnter() {
      this.onExport();
    },
  },
};
</script>

<style lang="scss">
  .input-number {
    width: 100%;
  }
</style>
