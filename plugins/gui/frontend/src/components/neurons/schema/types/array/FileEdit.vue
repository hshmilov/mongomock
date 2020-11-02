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
        :accept="acceptFileTypes"
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
import primitiveMixin from '@mixins/primitive';
import axiosClient from '@api/axios';
import { mapMutations } from 'vuex';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

export default {
  name: 'XFileEdit',
  mixins: [primitiveMixin],
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
      default: false,
    },
  },
  computed: {
    fileName() {
      return this.value && this.value.filename ? this.value.filename : 'No file chosen';
    },
    acceptFileTypes() {
      return this.schema && this.schema.format === 'image' ? 'image/*' : '*';
    },
  },
  data() {
    return {
      uploading: false,
      filename: '',
      filesize: 0,
      localError: '',
    };
  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    selectFile(e) {
      e.preventDefault();
      this.$refs.file.click();
    },
    uploadFile(uploadEvent) {
      const files = uploadEvent.target.files || uploadEvent.dataTransfer.files;
      let fileEndpoint = 'upload_file';
      if (this.schema.format === 'image') {
        fileEndpoint = 'upload_image_file';
      }
      if (!files.length) {
        this.valid = false;
        this.validate(false);
        return;
      }
      const file = files[0];
      const formData = new FormData();
      formData.append('field_name', this.schema.name);
      formData.append('userfile', file);
      this.filename = file.name;
      this.filesize = file.size;
      this.valid = true;
      this.validate(false);
      if (this.valid) {
        this.uploading = true;
        const uploadUrl = `${this.apiUpload}/${fileEndpoint}`;
        axiosClient.post(uploadUrl, formData).then((response) => {
          this.uploading = false;
          this.valid = true;
          this.validate(true);
          this.$emit('input', { uuid: response.data.uuid, filename: file.name });
        }).catch((response) => {
          this.uploading = false;
          this.valid = true;
          this.error = response.response.data.message;
          this.showToasterMessage({ message: this.error });
        });
      } else {
        this.showToasterMessage({ message: this.localError });
      }
    },
    removeFile() {
      this.$emit('input', null);
    },
    checkData() {
      if (this.schema.required && this.isEmpty()) {
        this.localError = `${this.schema.name} File is required`;
        return false;
      }
      if (this.schema.format === 'image' && this.filename) {
        if (this.filesize / 1000000 > 5) {
          this.localError = 'Image upload failed : file size exceeded maximum size';
          this.filename = '';
          this.filesize = 0;
          return false;
        }
        const fileParts = this.filename.split('.');
        const fileType = fileParts[fileParts.length - 1].toLowerCase();
        if (!['jpg', 'jpeg', 'png'].includes(fileType)) {
          this.localError = 'Image upload failed : unsupported file type';
          this.filename = '';
          this.filesize = 0;
          return false;
        }
      }
      this.localError = '';
      return true;
    },
    isEmpty() {
      return !(this.filename || (this.data && this.data.filename));
    },
    getErrorMessage() {
      return this.localError;
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
