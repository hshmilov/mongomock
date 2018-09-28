<template>
    <div class="upload-file">
        <template v-if="uploading">
            <div class="file-name">
                <svg-icon name="symbol/running" :original="true" height="20" class="rotating"/>
                <div class="name-placeholder">Uploading...</div>
            </div>
        </template>
        <template v-else>
            <input type="file" @change="uploadFile" @focusout="onFocusout" ref="file" :disabled="readOnly" />
            <div class="file-name" :class="{'error-border': error}">{{value ? value.filename : "No file chosen"}}</div>
            <div class="x-btn link" :class="{ disabled: readOnly }" @click="selectFile">Choose file</div>
        </template>
    </div>
</template>

<script>
    export default {
        name: 'x-array-edit',
        props: ['schema', 'value', 'apiUpload', 'readOnly'],
        data() {
            return {
                valid: !!this.value,
                error: '',
                uploading: false,
                filename: ""
            }
        },
        methods: {
        	selectFile() {
        	    if (this.readOnly) return
        		this.$refs.file.click()
            },
            uploadFile(uploadEvent) {
                const files = uploadEvent.target.files || uploadEvent.dataTransfer.files
                if (!files.length) {
                	this.valid = false
                    this.validate(false)
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
                    this.filename = file.name
                    this.valid = true
                    this.validate(true)
                    this.$emit('input', {"uuid": res.uuid, "filename": file.name})
                };
                request.send(formData)
            },
            validate(silent) {
                if (!this.schema.required) return

				this.error = ''
                if (!silent && !this.valid) {
                	this.error = `${this.schema.name} File is required`
                }
                this.$emit('validate', {
                	title: this.schema.title, valid: this.valid, error: this.error
                })
            },
            onFocusout() {
        		this.validate(false)
            }
        },
		destroyed() {
			this.valid = true
			this.error = ''
			this.validate(true)
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
            &.disabled {
                cursor: default;
            }
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
            .name-placeholder {
                display: inline-block;
            }
        }
    }
</style>