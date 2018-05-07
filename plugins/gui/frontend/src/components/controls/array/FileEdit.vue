<template>
    <div class="upload-file">
        <template v-if="uploading">
            <svg-icon name="action/lifecycle/running" :original="true" height="20" class="rotating"/>
        </template>
        <template v-else>
            <input type="file" @change="uploadFile" @focusout="updateValidity(fileUploaded)"
                   class="file-data" :class="{'invalid': !valid}"/>
            <div class="file-name">{{value ? value.filename : "No file chosen"}}</div>
        </template>
    </div>
</template>

<script>
	import '../../icons'
    export default {
        name: 'x-array-edit',
        props: ['schema', 'value', 'validator', 'apiUpload'],
        data() {
            return {
                valid: true,
                fileUploaded: !!this.value,
                uploading: false,
                filename: ""
            }
        },
        methods: {
            uploadFile(uploadEvent) {
                const files = uploadEvent.target.files || uploadEvent.dataTransfer.files
                if (!files.length) {
                    this.updateValidity(false)
                    return
                }
                var file = files[0]
                var formData = new FormData()
                formData.append("field_name", this.schema.name)
                formData.append("userfile", file)

                this.uploading = true


                var request = new XMLHttpRequest()
                request.open('POST', `/api/${this.apiUpload}/upload_file`)
                request.onload = (result) => {
                    var res = JSON.parse(result.srcElement.responseText)
                    this.uploading = false
                    this.fileUploaded = true
                    this.filename = file.name
                    this.updateValidity(true)
                    this.$emit('input', {"uuid": res.uuid, "filename": file.name})
                };
                request.send(formData)
            },
            updateValidity(valid) {
                if (!this.validator || !this.schema.required) {
                    return
                }
                this.valid = valid
                this.validator.$emit('validate', {title: this.schema.title, valid: valid})
            }
        }
    }
</script>

<style lang="scss">
    .upload-file {
        display: flex;
        .svg-stroke {
            stroke: $grey-3;
            stroke-width: 6px;
        }
        .file-data {
            width: 95px !important;
            border: 0 !important;
            height: 100%;
        }
        .file-name {
            border: 1px solid $grey-2;
            padding: 0 8px;
            line-height: 26px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }
    }
</style>