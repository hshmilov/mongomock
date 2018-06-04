<template>
    <div class="x-empty-system">
        <svg-icon name="illustration/see_all" :original="true" height="420"/>
        <div class="title">SEE ALL TO SECURE ALL</div>
        <div class="content">Congratulations! You are one step closer to<br>having all your assets visible in one place.</div>
        <div class="footer">
            <button @click="onClickTour" class="x-btn">SHOW ME HOW</button>
        </div>
    </div>
</template>

<script>
    import Modal from '../../popover/Modal.vue'

    import { mapMutations } from 'vuex'
    import { START_TOUR, UPDATE_TOUR_STATE, STOP_TOUR } from '../../../store/modules/onboarding'

	export default {
		name: 'x-empty-system',
        components: { Modal },
        data() {
			return {
				isActive: true
            }
        },
        methods: {
            ...mapMutations({ startTour: START_TOUR, updateState: UPDATE_TOUR_STATE, stopTour: STOP_TOUR }),
			onClickTour() {
				this.isActive = false
                this.startTour()
            },
            closeMessageModal() {
            	this.isActive = false
                this.stopTour()
            }
        },
        created() {
			this.updateState('')
        }
	}
</script>

<style lang="scss">
    .x-empty-system {
        text-align: center;
        .title {
            font-size: 24px;
            color: $theme-orange;
            margin-top: 48px;
            margin-bottom: 24px;
        }
        .content {
            margin-bottom: 56px;
        }
        .footer {
            text-align: center;
            .x-btn {
                width: auto;
            }
        }
    }
</style>