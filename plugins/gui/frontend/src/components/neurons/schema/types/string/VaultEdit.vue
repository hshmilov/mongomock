<template>
    <div>
        <x-string
                :schema="schema"
                v-model="processedData"
                :read-only="readOnly"
                @validate="onValidate"
                @input="input"
                @keydown="onKeyPress"
        >
            <template slot="icon">

                <div class='cyberark-icon' v-if="!loading">
                    <md-icon id="cyberark-button"
                            :class="{'error': error, 'success': success}"
                            md-src="/src/assets/icons/logo/cyberark_logo.svg"
                            @click.native="toggleQueryModal"
                            :title="getTooltip"
                    />
                </div>
                <div
                        v-if="loading"
                        class="loading-button"
                >
                    <md-progress-spinner
                            class="progress-spinner"
                            md-mode="indeterminate"
                            :md-stroke="3"
                            :md-diameter="30"
                    />
                </div>
            </template>
        </x-string>
        <x-modal v-if="queryModal.open"
                 @close="toggleQueryModal"
                 @confirm="TestValueQuery"
                 approve-text="Fetch"
                 size="md"
        >

            <div slot="body">
                <x-title :logo="`adapters/cyberark`">
                    CyberArk Vault
                </x-title>
                <label for="cyberark-query">Query:</label>
                <textarea id="cyberark-query" v-model="queryModal.current_query" rows="3"/>
            </div>
        </x-modal>
    </div>
</template>

<script>
    import primitiveMixin from '../primitive.js'
    import XString from './StringEdit.vue'
    import xModal from '../../../../axons/popover/Modal.vue'
    import {parseVaultError} from '../../../../../constants/utils'
    import axios from 'axios'

    import XTitle from "../../../../axons/layout/Title.vue";

    export default {
        name: "XVaultEdit",
        components: {XTitle, XString, xModal},
        mixins: [primitiveMixin],
        data ()  {
            return {
                queryModal: {
                    open: false,
                    current_query: ''
                },
                passString: '',
                error: '',
                success: false,
                loading: false
            }
        },
        computed: {
            processedData: {
                get() {
                    return this.isUnchangedPassword ? '********' : this.data
                },
                set(new_val) {
                    this.data = new_val
                }
            },
            getTooltip () {
                if (this.data && this.error) return this.error
                if (this.data && this.success) return this.queryModal.current_query
                return 'Use CyberArk Vault'
            },
            isUnchangedPassword () {
                return this.inputType === 'password' && this.data && this.data[0] === 'unchanged'
            },
        },
        methods: {
            toggleQueryModal() {
                this.queryModal.open = !this.queryModal.open
            },
            TestValueQuery() {
                this.toggleQueryModal()
                this.success = false
                this.error = ''
                this.loading = true
                this.data = {query: this.queryModal.current_query, type: 'cyberark_vault'}
                axios.post('/api/password_vault', {
                        query: this.queryModal.current_query,
                        field: this.schema.name,
                        vault_type: 'cyberark_vault'
                }).then((testRes) => {
                    if (!testRes) return
                    this.success = true
                    this.data = {query: this.queryModal.current_query, type: 'cyberark_vault'}
                    this.input()
                    this.validate()
                }).catch((recievedError) => {
                    this.success = false
                    let result = parseVaultError(recievedError.response.data.message)
                    // this.validate(true)
                    this.error = result[2]
                }).finally(() => {
                    this.loading = false
                })
            },
            onValidate (validity) {
                this.$emit('validate', validity)
            },
            onKeyPress (event) {
                // if (event.code !== 'Backspace' && event.code !== 'Delete') return
                if (!this.queryModal.current_query) return;
                this.queryModal.current_query = ''
                this.data = ''
                this.success = false
                this.input()
            },
            checkData () {
                return this.success || this.schema.required
            }
        },
        mounted() {
            if (this.value && this.value.query) {
                this.data = this.value
                this.queryModal.current_query = this.data.query
                if (this.value.error) {
                    this.error = this.value.error
                } else {
                    this.success = true
                }
            }
        }
    }
</script>

<style lang="scss">

    .string-input-container {
        position: relative;

        .cyberark-icon {
            border: 0;
            position: absolute;
            right: 0;
            margin-right: 12px;
            z-index: 100;
            line-height: 24px;
            cursor: pointer;
            border-radius: 80%;
            margin-top: 0;
            top: 1px;

            .svg-fill {
                fill: $grey-4
            }

            .svg-stroke {
                stroke: $grey-4
            }

            .error {
                background-color: transparent !important;
            }

            .success {
                background-color: transparent !important;
            }

            .md-icon.error .svg-stroke {
                stroke: $indicator-error;
            }
            .md-icon.success .svg-stroke {
                stroke: $indicator-success;
            }
        }

        .md-progress-spinner-circle {
            stroke: #0076FF;
            border: 0;
            position: absolute;
            right: 0;
            margin-right: 12px;
            top: 0;
            z-index: 100;
            line-height: 24px;
            cursor: pointer;
            border-radius: 80%;
        }
        .loading-button {
            border: 0;
            position: absolute;
            right: 0;
            margin-right: 12px;
            top: 1px;
            z-index: 100;
            line-height: 24px;
            cursor: pointer;
            border-radius: 80%;

            .progress-spinner {
                top: 1px;
                height: 19px;

                .md-progress-spinner-draw {
                    width: 19px !important;
                    height: 19px !important;;
                }
            }
        }
    }
    #cyberark-query {
        resize: none;
    }
</style>