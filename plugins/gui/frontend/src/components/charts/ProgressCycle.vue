<template>
    <div>
        <div class="progress-cycle" :class="completeClasses">
            <div class="content complete" v-if="complete === 100">
                <div class="title">System is stable</div>
                <i class="icon-checkmark2 remaining"></i>
            </div>
            <div v-else-if="remaining" class="content">
                <div class="title">Adapters left to complete phase:</div>
                <div class="remaining">{{remaining}}</div>
            </div>
        </div>
        <div v-for="part, ind in parts" :class="`parts part-${ind + 1}`">{{part.split('_').join(' ')}}</div>
    </div>
</template>

<script>
	export default {
		name: 'x-progress-cycle',
        props: ['complete', 'parts', 'remaining'],
        computed: {
			completeClasses() {
				let classList = ['fill-top']
                if (this.complete < 25) {
					classList.push('hide-top')
                    classList.push(this.remainderClass(25))
				} else {
                    classList.push('fill-right')
                    if (this.complete < 50) {
                        classList.push('hide-right')
                        classList.push(this.remainderClass(50))
                    } else {
                        classList.push('fill-bottom')
                        if (this.complete < 75) {
                            classList.push('hide-bottom')
                            classList.push(this.remainderClass(75))
                        } else {
                            classList.push('fill-left')
                            if (this.complete < 100) {
                                classList.push('hide-left')
                                classList.push(this.remainderClass(100))
                            }
                        }
                    }
                }
                return classList.join(' ')
            }
        },
        methods: {
			remainderClass(threshold) {
				return 'turn-' + (threshold - this.complete)
			}
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .progress-cycle {
        height: 200px;
        width: 200px;
        border: solid 24px $gray-light;
        background: transparent;
        border-radius: 100%;
        display: inline-block;
        margin: 1em;
        position: relative;
        transform: rotate(45deg);
        &:before, &:after {
            content:'';
            position:absolute;
            top: -24px;
            left: -24px;
            border: solid 24px transparent;
            height: inherit;
            width: inherit;
            border-radius: inherit;
        }
        &.fill-top {  border-top-color: $success-colour;  }
        &.hide-top:before {  border-top-color: $gray-light;  }
        &.fill-right {  border-right-color: $success-colour;  }
        &.hide-right:before {  border-right-color: $gray-light;  }
        &.fill-bottom {  border-bottom-color: $success-colour;  }
        &.hide-bottom:before {  border-bottom-color: $gray-light;  }
        &.fill-left {  border-left-color: $success-colour;  }
        &.hide-left:before {  border-left-color: $gray-light;  }

        &.turn-20:before {  transform: rotate(18deg);  }
        &.turn-15:before {  transform: rotate(36deg);  }
        &.turn-10:before {  transform: rotate(54deg);  }
        &.turn-5:before {  transform: rotate(72deg);  }

        .content {
            transform: rotate(-45deg);
            margin-top: 40px;
            margin-left: 24px;
            width: 120px;
            color: $info-colour;
            &.complete {
                margin-top: 56px;
            }
            .title {
                font-size: 14px;
            }
            .remaining {
                font-size: 24px;
                font-weight: 300;
                margin-top: 4px;
                display: block;
            }
        }
    }

    .parts {
        position: absolute;
        font-size: 12px;
        width: 84px;
        &:after {
            content: '';
            position: absolute;
            right: 50%;
            top: 42px;
            width: 2px;
            height: 24px;
            background-color: $gray-dark;
        }
        &.part-1 {
            top: 4px;
            left: 139px;
            &:after {  top: 24px;  }
        }
        &.part-2 {
            transform: rotate(72deg);
            right: 20px;
            top: 72px;
        }
        &.part-3 {
            transform: rotate(145deg);
            right: 68px;
            top: 206px;
            &:after {  top: 38px;  }
        }
        &.part-4 {
            transform: rotate(-145deg);
            left: 68px;
            top: 206px;
            &:after {  top: 38px;  }
        }
        &.part-5 {
            transform: rotate(-72deg);
            left: 20px;
            top: 72px;
        }
    }

</style>