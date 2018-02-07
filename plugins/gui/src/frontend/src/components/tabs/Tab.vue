<template>
    <div v-show="isActive" class="tab-pane" :class="{'active': isActive}" role="tabpanel">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'tab',
		props: {
			'id': {required: true}, 'title': {required: true}, 'selected': {default: false},
			'logo': {}, 'outdated': {default: false}
		},
		data () {
			return {
				isActive: false
			}
		},
		created () {
			this.isActive = this.selected
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .tab-pane {
        background-color: $color-light;
        border: 1px solid #ddd;
        border-top: 0;
        border-bottom-right-radius: 4px;
        border-bottom-left-radius: 4px;
        padding: 12px;
    }

</style>