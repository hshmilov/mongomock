<template>
    <div class="x-checkbox" :class="{'x-checked': checked}" @click.stop="$refs.checkbox.click()">
        <div class="x-checkbox-container" :class="{'x-checkbox-semi': semi}">
            <input type="checkbox" v-model="checked" @change="updateData" ref="checkbox">
        </div>
    </div>
</template>

<script>
	export default {
		name: 'x-checkbox',
        props: {data: {}, value: {default: 'on'}, semi: {default: false}},
        model: {
			prop: 'data',
            event: 'change'
        },
        data() {
			return {
				checked: false
            }
        },
        watch: {
			data(newData) {
				this.updateChecked(newData)
            }
        },
        methods: {
			change(data) {
				this.$emit('change', data)
			},
			updateData() {
				if (Array.isArray(this.data) && !Array.isArray(this.value)) {
					if (this.checked) {
						this.change(this.data.concat([this.value]))
                        return
					}
                    let index = this.data.indexOf(this.value)
                    if (index > -1) {
						let temp = [ ...this.data ]
                        temp.splice(index, 1)
						this.change(temp)
					}
				} else if (typeof this.data === 'boolean') {
                    this.change(this.checked)
                } else {
					this.change(this.checked? this.value : (Array.isArray(this.data)? []: null))
                }
            },
            updateChecked(data) {
                this.checked = ((Array.isArray(data) && !Array.isArray(this.value) && data.includes(this.value)) ||
					(typeof data === 'boolean' && data) ||
					(data === this.value))
            }
        },
        created() {
			this.updateChecked(this.data)
        }
	}
</script>

<style lang="scss" scoped>
    .x-checkbox {
        cursor: pointer;
        .x-checkbox-container {
            width: 20px;
            min-width: 20px;
            height: 20px;
            position: relative;
            border-radius: 2px;
            border: 2px solid $theme-gray-dark;
            transition: .4s cubic-bezier(.25,.8,.25,1);
            input {
                position: absolute;
                left: -999em;
            }
            &:after {
                width: 6px;
                height: 13px;
                top: 0;
                left: 5px;
                z-index: 7;
                border: 2px solid transparent;
                border-top: 0;
                border-left: 0;
                opacity: 0;
                -webkit-transform: rotate(45deg) scale3D(.15,.15,1);
                transform: rotate(45deg) scale3D(.15,.15,1);
                position: absolute;
                transition: .4s cubic-bezier(.55,0,.55,.2);
                content: ' ';
            }
            &.x-checkbox-semi {
                background-color: $theme-black;
                border-color: $theme-black;
                &:after {
                    opacity: 1;
                    width: 2px;
                    height: 10px;
                    top: 3px;
                    left: 7px;
                    -webkit-transform: rotate(90deg) scale3D(1,1,1);
                    transform: rotate(90deg) scale3D(1,1,1);
                    transition: .4s cubic-bezier(.25,.8,.25,1);
                    border-color: $theme-white;
                }
            }
        }
        &.x-checked .x-checkbox-container {
            background-color: $theme-black;
            border-color: $theme-black;
            &:after {
                opacity: 1;
                -webkit-transform: rotate(45deg) scale3D(1,1,1);
                transform: rotate(45deg) scale3D(1,1,1);
                transition: .4s cubic-bezier(.25,.8,.25,1);
                border-color: $theme-white;
            }
        }
    }
</style>