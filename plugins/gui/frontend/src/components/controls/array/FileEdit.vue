<template>
    <div class="upload-file">
        <template v-if="uploading">
            <div class="file-name">
                <svg-icon name="action/lifecycle/running" :original="true" height="20" class="rotating"/>
                <div>Uploading...</div>
            </div>
        </template>
        <template v-else>
            <input type="file" @change="uploadFile" @focusout="updateValidity(fileUploaded)" ref="file"/>
            <div class="file-name" :class="{'invalid': !valid}">{{value ? value.filename : "No file chosen"}}</div>
            <div class="x-btn link" @click="selectFile">Choose file</div>
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
        	selectFile() {
        		this.$refs.file.click()
            },
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
        input[type=file] {
            position: absolute;
            left: -999em;
        }
        .x-btn.link {
            color: $theme-black;
            font-size: 12px;
            font-weight: 200;
        }
        .file-name {
            border: 1px solid $grey-2;
            padding: 0 8px;
            line-height: 26px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            .svg-icon {
                margin-right: 8px;
                .svg-stroke {
                    stroke: $grey-3;
                    stroke-width: 6px;
                }
            }
        }
    }
</style>