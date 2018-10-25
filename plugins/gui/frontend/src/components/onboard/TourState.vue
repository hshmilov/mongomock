<template>
    <div class="x-tour-state" :style="position" v-if="tourActive && currentState">
        <div class="state-tip" :class="alignClass">
            <div class="header">
                <div class="remove"><div @click="stopTour">x</div></div>
                <div class="title">{{currentState.title || '&nbsp;'}}</div>
            </div>
            <div class="content">{{currentState.content}}</div>
            <div class="actions">
                    <button v-for="action in currentState.actions" @click="changeState({name: action.state})" class="x-btn">
                    {{action.title}}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
    import { mapState, mapMutations } from 'vuex'
    import { STOP_TOUR, CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

	export default {
		name: 'x-tour-state',
        props: {},
        computed: {
            ...mapState({
                currentState(state) {
                	return state.onboarding.tourStates.defs[state.onboarding.tourStates.current]
                },
				tourActive(state) {
					return state.onboarding.tourStates.active
				}
            }),
            alignElement() {
            	if (!this.tourActive || !this.currentState || !this.currentState.id || this.currentState.align === 'center') {
            		return null
				}
            	return document.getElementById(this.currentState.id)
            }
        },
        data() {
			return {
				position: {},
                alignClass: ''
			}
        },
        watch: {
			alignElement(newElement, oldElement) {
			    if (oldElement) {
			    	oldElement.classList.remove('pulsing')
                }
                if (newElement && (this.currentState.emphasize === undefined || this.currentState.emphasize)) {
			    	newElement.classList.add('pulsing')
                }
            },
            currentState() {
                this.alignClass = ''
            }
        },
        methods: {
            ...mapMutations({ stopTour: STOP_TOUR, changeState: CHANGE_TOUR_STATE }),
            calcPosition() {
                let selfHeight = this.$el.offsetHeight
                let selfWidth = this.$el.offsetWidth
				if (!this.alignElement) {
					this.position = { left: `calc(50vw - ${selfWidth/2}px)`, top: '24vh' }
					return
				}
                this.alignElement.scrollIntoView(false)
				let align = {
					top: this.calcOffsetTop(this.alignElement) - this.calcScrollTop(this.alignElement),
                    left: this.calcOffsetLeft(this.alignElement),
                    height: this.alignElement.offsetHeight,
                    width: this.alignElement.offsetWidth
				}
				if (this.currentState.align === 'right' || this.currentState.align === 'left') {
					let top = (align.top + align.height/2 - selfHeight/2) + 'px'
					if (this.currentState.align === 'right') {
						this.position = { top, left: align.left + align.width + 'px' }
					} else {
					    this.position = { top, left: align.left - selfWidth + 'px' }
                    }
				} else  {
					let left = (align.left + align.width/2 - selfWidth/2) + 'px'
					if (this.currentState.align === 'bottom') {
					    this.position = { top: (align.top + align.height) + 'px', left }
					} else {
						this.position =  { top: align.top - selfHeight + 'px', left }
                    }
				}
            },
            calcOffsetTop(element) {
            	if (element == null) {
            		return 0
                }
                let offset = element.offsetTop + this.calcOffsetTop(element.offsetParent)
                if (this.currentState.fixed) {
                    offset -= parseInt(window.getComputedStyle(element, null).getPropertyValue('padding-top'))
                }
                return offset
            },
            calcScrollTop(element) {
            	if (this.currentState.fixed) return 0

            	if (element.parentElement == null) {
            		return element.scrollTop
                }
                return element.scrollTop + this.calcScrollTop(element.parentElement)
            },
			calcOffsetLeft(element) {
				if (element.offsetParent == null) {
					return element.offsetLeft
				}
				return element.offsetLeft + this.calcOffsetLeft(element.offsetParent)
			}
        },
        updated() {
			if (!this.alignClass && this.currentState) {
				this.alignClass = this.currentState.align
				this.calcPosition()
            }
        }
	}
</script>

<style lang="scss">
    .x-tour-state {
        position: absolute;
        padding: 20px;
        min-height: 120px;
        max-width: 360px;
        .state-tip {
            position: relative;
            z-index: 2000;
            padding: 24px;
            background: $theme-black;
            color: $grey-1;
            border-radius: 4px;
            box-shadow: $popup-shadow;
            .header {
                margin-bottom: 8px;
                .title {
                    color: $theme-orange;
                    display: inline-block;
                    font-size: 20px;
                }
                .remove {
                    margin-right: -12px;
                    margin-top: -12px;
                    color: $grey-3;
                    cursor: pointer;
                    line-height: 14px;
                    text-align: right;
                    &:hover {
                        color: $grey-1;
                    }
                }
            }
            .content {
                white-space: pre-line;
            }
            .actions {
                margin-top: 12px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                grid-gap: 8px;
                .x-btn {
                    width: auto;
                }
            }
            &:not(.center):before {
                content: '';
                position: absolute;
                height: 20px;
                width: 20px;
                box-shadow: $popup-shadow;
                transform: rotate(45deg);
                background-color: $theme-black;
            }
            &:not(.center):after {
                content: '';
                position: absolute;
                background-color: $theme-black;
            }
            &.center {
                animation: bounceY 1s ease;
            }
            &.right, &.left {
                animation: bounceX 1s ease;
                &:before {
                    top: calc(50% - 10px);
                }
                &:after {
                    top: calc(50% - 15px);
                    height: 30px;
                    width: 20px;
                }
            }
            &.right {
                &:before { left: -10px; }
                &:after { left: 0; }
            }
            &.left {
                &:before { right: -10px; }
                &:after { right: 0; }
            }
            &.top, &.bottom {
                animation: bounceY 1s ease;
                &:before {
                    left: calc(50% - 10px);
                }
                &:after {
                    left: calc(50% - 15px);
                    width: 30px;
                    height: 20px;
                }
            }
            &.top {
                &:before { bottom: -10px; }
                &:after { bottom: 0; }
            }
            &.bottom {
                &:before { top: -10px; }
                &:after { top: 0; }
            }
        }
    }
</style>