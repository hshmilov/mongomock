<template>
    <div v-show="isActive" :class="{'active': isActive, [ id ]: true}" class="x-tab" role="tabpanel">
        <slot></slot>
    </div>
</template>

<script>
    export default {
        name: 'x-tab',
        props: {
            'id': {required: true}, 'title': {required: true}, 'selected': {default: false},
            'logo': {}, 'outdated': {default: false}
        },
        data() {
            return {
                isActive: false
            }
        },
        created() {
            this.isActive = this.selected
        }
    }
</script>

<style lang="scss">
    .x-tab {
        height: 100%;
    }

</style>