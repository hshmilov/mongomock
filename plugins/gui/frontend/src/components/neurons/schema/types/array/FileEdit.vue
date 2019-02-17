<template>
    <div class="upload-file">
        <template v-if="uploading">
            <div class="file-name">
                <svg-icon name="symbol/running" :original="true" height="20" class="rotating"/>
                <div class="name-placeholder">Uploading...</div>
            </div>
        </template>
        <template v-else>
            <input type="file" @change="uploadFile" @focusout="onFocusout" ref="file" :disabled="readOnly" :id="schema.name" />
            <div class="file-name" :class="{'error-border': error}">{{value ? value.filename : "No file chosen"}}</div>
            <x-button link :disabled="readOnly" @click="selectFile">Choose file</x-button>
        </template>
    </div>
</template>

<script>
    import xButton from '../../../../axons/inputs/Button.vue'

    import {currentHost} from '../../../../../store/actions'

    export default {
        name: 'x-array-edit',
        components: { xButton },
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
                event.preventDefault()
        		this.$refs.file.click()
            },
            uploadFile(uploadEvent) {
                const files = uploadEvent.target.files || uploadEvent.dataTransfer.files
                if (!files.length) {
                	this.valid = false
                    this.validate(false)
                    return
                }
                let file = files[0]
                let formData = new FormData()
                formData.append("field_name", this.schema.name)
                formData.append("userfile", file)

                this.uploading = true
                let request = new XMLHttpRequest()
                request.open('POST', `${currentHost}/api/${this.apiUpload}/upload_file`)
                request.onload = (result) => {
                    let res = JSON.parse(result.srcElement.responseText)
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
        position: relative;
        input[type=file] {
            position: absolute;
            left: 0;
            top: 0;
            z-index: 0;
        }
        .x-button.link {
            color: $theme-black;
            font-size: 12px;
            font-weight: 200;
            &.disabled {
                cursor: default;
            }
        }
        .file-name {
            border: 1px solid $grey-2;
            background: $theme-white;
            z-index: 2;
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
    .x-form .x-array-edit .object .upload-file input {
        width: 10px;
    }
</style>