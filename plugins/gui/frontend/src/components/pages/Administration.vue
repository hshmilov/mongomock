<template>
  <XPage
    title="Administration"
    class="x-administration"
  >
    <h5 class="x-administration-title">
      Customer ID
    </h5>
    <p class="x-administration-text">
      {{ customerId }}
    </p>
    <h5 class="x-administration-title">
      Upload Configuration Script
    </h5>
    <div class="x-administration-file-upload">
      <FilePond
        ref="pond"
        name="test"
        class-name="my-pond"
        :label-idle="label"
        :chunk-size="100000000"
        :max-files="1"
        @processfile="handleFilePondProcess"
        @addfile="handleFilePondFileAdd"
        @removefile="handleFilePondRemove"
      />
    </div>
    <XButton
      id="execute_script"
      :disabled="!uploaded"
      title="Run"
      @click="handleFileExecution"
    >Run</XButton>
    <div
      v-if="message"
      class="x-administration-error"
    >{{ message }}</div>
  </XPage>
</template>
<script>
import vueFilePond, { setOptions } from 'vue-filepond';
import 'filepond/dist/filepond.min.css';
import XPage from '@axons/layout/Page.vue';
import { executeFile, processFileUploadInChunks } from '@api/execute-configuration';
import { mapMutations, mapState } from 'vuex';
import _get from 'lodash/get';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';

const FilePond = vueFilePond();

setOptions({
  server: {
    url: '/upload_file',
    process: processFileUploadInChunks,
    revert: '',
    restore: null,
    load: null,
    fetch: null,
  },
});

export default {
  name: 'XAdministration',
  components: { XPage, FilePond },
  data() {
    return {
      uploaded: false,
      fileServerId: '',
      message: '',
      label: `<svg width="21px" height="15px" viewBox="0 0 21 15" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
                    <g id="Page-1" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" stroke-linecap="round" stroke-linejoin="round">
                        <g id="icon" stroke="#4f4f4f">
                            <path d="M16.5,11.5 L17,11.5 C18.933,11.5 20.5,9.933 20.5,8 C20.5,6.067 18.933,4.5 17,4.5 C16.929,4.5 16.863,4.517 16.793,4.521 C16.146,2.203 14.024,0.5 11.5,0.5 C9.51,0.5 7.771,1.561 6.806,3.145 C6.552,3.058 6.284,3 6,3 C4.619,3 3.5,4.119 3.5,5.5 C1.843,5.5 0.5,6.843 0.5,8.5 C0.5,10.157 1.843,11.5 3.5,11.5 L4.5,11.5 M10.5,5.5 L10.5,14.5 M13.5,8.5 L10.5,5.5 L7.5,8.5" id="lineart"></path>
                        </g>
                    </g>
                </svg><div>Drag and drop a file or click to upload</div>`,
    };
  },
  computed: {
    ...mapState({
      customerId(state) {
        return _get(state, 'configuration.data.global.customerId', '');
      },
    }),
  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    handleFilePondProcess(error, file) {
      if (error) {
        this.message = `Configuration script upload failed: ${error.body}`;
      }
      this.uploaded = true;
      this.fileServerId = file.serverId;
    },
    handleFilePondFileAdd(error) {
      if (error) {
        this.message = error;
      }
      this.uploaded = false;
      this.message = '';
    },
    async handleFileExecution() {
      try {
        await executeFile(this.fileServerId);
        this.uploaded = false;
        this.$refs.pond.removeFile();
        this.showToasterMessage({ message: 'Script execution has begun' });
      } catch (error) {
        this.message = error;
      }
    },
    handleFilePondRemove(error) {
      if (error) {
        this.message = error;
      } else {
        this.fileServerId = '';
        this.message = '';
      }
      this.uploaded = false;
    },
  },
};
</script>

<style lang="scss">
  .x-administration {
    .x-administration-title {
      font-size: 16px;
      font-weight: bold;
      margin-bottom: 5px;
    }
    .x-administration-text {
      font-size: 14px;
      margin-bottom: 5px;
    }
    .x-administration-error {
      margin: 5px 0;
      color: $indicator-error;
      font-weight: 300;
    }
    .x-administration-file-upload {
      width: 400px;
    }
    .filepond--panel-root {
      border: 1px dashed $grey-3;
    }
    .filepond--root {
      font-family: Roboto, serif;
    }
    .filepond--drop-label label {
      font-weight: 300;
    }
  }
</style>
