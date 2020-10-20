<template>
  <div class="x-file-edit">
    <template v-if="uploading">
      <div class="file">
        <XIcon
          family="symbol"
          type="running"
          spin
        />
        <div class="name-placeholder">
          Uploading...
        </div>
      </div>
    </template>
    <template v-else>
      <input
        :id="schema.name"
        ref="file"
        type="file"
        :disabled="readOnly"
        @change="uploadFile"
        @focusout="onFocusout"
      >
      <div
        class="file"
        :title="fileName"
        :class="{'error-border': error}"
      >
        <div class="file__name">{{ fileName }}</div>
        <div v-if="!readOnly && value && value.filename" class="file__remove">
          <XButton
            type="link"
            @click="removeFile"
          >x</XButton>
        </div>
      </div>
      <XButton
        type="link"
        :disabled="readOnly"
        @click="selectFile"
      >
        Choose file
      </XButton>
    </template>
  </div>
</template>

<script>
import axiosClient from '@api/axios';

export default {
  name: 'XFileEdit',
  props: {
    schema: {
      type: Object,
      required: true,
    },
    value: {
      type: Object,
      default: () => ({}),
    },
    apiUpload: {
      type: String,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false
    },
  },
  computed: {
    fileName() {
      return this.value && this.value.filename ? this.value.filename : 'No file chosen';
    },
  },
  data() {
    return {
      valid: !!this.value,
      error: '',
      uploading: false,
      filename: '',
    };
  },
  methods: {
    selectFile(e) {
      e.preventDefault();
      this.$refs.file.click();
    },
    uploadFile(uploadEvent) {
      const files = uploadEvent.target.files || uploadEvent.dataTransfer.files;
      if (!files.length) {
        this.valid = false;
        this.validate(false);
        return;
      }
      const file = files[0];
      const formData = new FormData();
      formData.append('field_name', this.schema.name);
      formData.append('userfile', file);

      this.uploading = true;
      const uploadUrl = `${this.apiUpload}/upload_file`;
      axiosClient.post(uploadUrl, formData).then((response) => {
        this.uploading = false;
        this.filename = file.name;
        this.valid = true;
        this.validate(true);
        this.$emit('input', { uuid: response.data.uuid, filename: file.name });
      });
    },
    removeFile() {
      this.$emit('input', null);
    },
    validate(silent) {
      if (!this.schema.required) return;

      this.error = '';
      if (!silent && !this.valid) {
        this.error = `${this.schema.name} File is required`;
      }
      this.$emit('validate', {
        name: this.schema.name, valid: this.valid, error: this.error,
      });
    },
    onFocusout() {
      this.validate(false);
    },
  },
};
</script>

<style lang="scss">
  .x-file-edit {
    display: flex;
    position: relative;

    input[type=file] {
      position: absolute;
      left: 0;
      top: 0;
      z-index: 0;
      display: none;
    }

    .x-button.ant-btn-link {
      color: $theme-black;
      font-size: 12px;
      font-weight: 200;
      line-height: 30px;

      &:disabled {
        cursor: default;
      }
    }

    .file {
      border: 1px solid $grey-2;
      background: $theme-white;
      z-index: 2;
      height: 30px;
      line-height: 30px;
      padding: 8px 4px;
      display: flex;
      align-items: center;
      width: 240px;

      &__name {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }

      &__remove {
        flex: 1;
        margin-left: 4px;
        display: flex;
        justify-content: flex-end;

        .x-button {
          padding: 0;
          display: flex;
          align-items: center;
        }
      }

      .x-icon {
        margin-right: 8px;
        vertical-align: super;

        .svg-stroke {
          stroke: $grey-3;
          stroke-width: 6px;
        }
      }
    }
  }

  .x-form .x-array-edit .object .x-file-edit input {
    width: 10px;
  }

</style>
