<template>
    <input type="file" @change="uploadFile" :class="{'invalid': !valid}" @focusout="updateValidity(fileUploaded)"/>
</template>

<script>
	export default {
		name: 'x-array-edit',
        props: ['schema', 'value', 'validator'],
        data() {
			return {
                valid: true,
                fileUploaded: !!this.value
            }
        },
        methods: {
			uploadFile(uploadEvent) {
				const files = uploadEvent.target.files || uploadEvent.dataTransfer.files
				if (!files.length) {
					this.updateValidity(false)
                    return
                }

				let reader = new FileReader()
				reader.onload = (loadEvent) => {
					this.$emit('input', Array.prototype.slice.call(new Uint8Array(loadEvent.target.result)))
                    this.fileUploaded = true
                    this.updateValidity(true)
				}
				reader.readAsArrayBuffer(files[0])
			},
            updateValidity(valid) {
				if (!this.validator || !this.schema.required) { return }
				this.valid = valid
				this.validator.$emit('validate', { title: this.schema.title, valid: valid })
            }
        }
	}
</script>

<style lang="scss">

</style>