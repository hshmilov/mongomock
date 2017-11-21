<template>
    <scrollable-page :title="`alerts > ${alertData.name? alertData.name : 'new'} alert`">
        <card title="alert configuration" class="alert-config">
            <template slot="cardContent">
                <div class="row">
                    <div class="form-group col-6">
                        <label class="form-label" for="alertName">Alert Name:</label>
                        <input class="form-control" id="alertName" v-model="alertData.name">
                    </div>
                    <div class="form-group col-6">
                        <label class="form-label" for="alertQuery">Select Query:</label>
                        <select class="form-control" id="alertQuery" v-model="alertData.query">
                            <option v-for="query in savedQueryOptions" :value="query.value">{{query.name}}</option>
                        </select>
                    </div>
                </div>
                <div class="row row-divider">
                    <div class="form-group col-6">
                        <div class="form-section-header">
                            <i class="icon-equalizer2"></i><span class="form-section-title">Test Condition</span>
                        </div>
                        <checkbox label="Devices result increases" v-model="alertCondition.increase"
                                  @change="updateCriteria()"></checkbox>
                        <checkbox label="Devices result decreases" v-model="alertCondition.decrease"
                                  @change="updateCriteria()"></checkbox>
                    </div>
                </div>
                <div class="row row-divider">
                    <div class="form-group col-6">
                        <div class="form-section-header">
                            <i class="icon-bell-o"></i><span class="form-section-title">Trigger Action</span>
                        </div>
                        <checkbox label="Add a notification" v-model="alertData.action.notification"></checkbox>
                    </div>
                    <a class="btn" @click="saveAlert">save</a>
                </div>
            </template>
        </card>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import Checkbox from '../../components/Checkbox.vue'

    import { mapState, mapGetters, mapActions } from 'vuex'
    import { FETCH_SAVED_QUERIES } from '../../store/modules/query'
    import { INSERT_ALERT } from '../../store/modules/alert'

	export default {
		components: { ScrollablePage, Card, Checkbox },
		name: 'alert-config-container',
        computed: {
            ...mapState([ 'alert', 'query' ]),
            ...mapGetters([ 'savedQueryOptions' ])
        },
        data() {
			return {
				alertData: {
                    id: this.$route.params.id,
                    name: '',
                    criteria: undefined,
                    query: '',
                    action: {
                    	notification: false
                    },
                    retrigger: false
                },
                alertCondition: {
					increase: false,
                    decrease: false
                }
            }
		},
        methods: {
            ...mapActions({ fetchQueries: FETCH_SAVED_QUERIES, insertAlert: INSERT_ALERT }),
            updateCriteria() {
				if (this.alertCondition.increase && this.alertCondition.decrease) {
					this.alertData.criteria = 0
				}
				if (this.alertCondition.increase && !this.alertCondition.decrease) {
					this.alertData.criteria = 1
				}
				if (!this.alertCondition.increase && this.alertCondition.decrease) {
					this.alertData.criteria = -1
				}
            },
            updateCondition() {
            	if (this.alertData.criteria <= 0) {
					this.alertCondition.decrease = true
                }
				if (this.alertData.criteria >= 0) {
					this.alertCondition.increase = true
				}
            },
			saveAlert() {
				if (this.alertData.criteria === undefined) {
					return
                }
                if (!this.alertData.name) {
					return
                }
                this.insertAlert(this.alertData)
				this.$router.push({name: 'Alerts'})
            }
        },
        created() {
			if (this.alert.currentAlert.data.id === this.alertData.id) {
				this.alertData = { ...this.alertData, ...this.alert.currentAlert.data }
				this.updateCondition()
			}
			if (!this.savedQueryOptions || !this.savedQueryOptions.length) {
				this.fetchQueries({})
            }
        }
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .alert-config {
        .row {
            position: relative;
            .form-group {
                padding: 12px 24px;
                .form-section-header {
                    color: $color-theme;
                    font-size: 20px;
                    .form-section-title {
                        margin-left: 8px;
                    }
                }
                .checkbox {
                    margin: 12px 24px;
                }
            }
            .btn {
                position: absolute;
                bottom: 0;
                right: 24px;
            }
        }
    }
</style>