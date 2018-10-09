<template>
    <modal v-if="value" @close="dismissAccessMessage">
        <div slot="body">You do not have permission to access the {{ value }} screen</div>
        <div slot="footer"><button class="x-btn" @click="dismissAccessMessage">OK</button></div>
    </modal>
</template>

<script>
    import Modal from './Modal.vue'

    export default {
        name: 'x-access-modal',
        components: { Modal },
        props: { value: {} },
        methods: {
            dismissAccessMessage() {
                this.$emit('input', '')
            }
        }
    }
</script>

<style lang="scss">

</style>