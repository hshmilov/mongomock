import Promise from 'promise'
import {REQUEST_API, FETCH_DATA_CONTENT, downloadPdfReportFile} from '../actions'

export const FETCH_REPORT = 'FETCH_REPORT'
export const SET_REPORT = 'SET_REPORT'
export const SAVE_REPORT = 'SAVE_REPORT'
export const REMOVE_REPORTS = 'REMOVE_REPORTS'
export const RUN_REPORT = 'RUN_REPORT'
export const DOWNLOAD_REPORT = 'DOWNLOAD_REPORT'

export const reports = {
    state: {
        /* Reports DataTable State */
        content: { data: [], fetching: false, error: ''},
        count: { data: 0, fetching: false, error: ''},
        view: {
            page: 0, pageSize: 20, fields: [], coloumnSizes: [],
            query: {
                filter: '', expressions: []
            },
            sort: {
                field: '', desc: true
            }
        },
        /* Data of Report currently being configured */
        current: { fetching: false, data: {}, error: '' }
    },

    mutations: {
        [ SET_REPORT ] (state, reportData) {
            /*
                Set given data, if given, or a new Report otherwise, as Report in the handle
             */
            if (reportData) {
                state.current.data = { ...reportData }
            } else {
                state.current.data = {

                }
            }
        }
    },
    actions: {
        [ FETCH_REPORT ] ({dispatch, commit}, reportId) {
            /*
                Ask server for a complete, specific report, if given an actual ID.
                Set the response as the report in handling.
                Otherwise, initialize a new report to handle.
             */
            if (!reportId || reportId === 'new') {
                return new Promise((resolve) => {
                    commit(SET_REPORT)
                    resolve()
                })
            }

            return dispatch(REQUEST_API, {
                rule: `reports/${reportId}`
            }).then((response) => {
                if (response.status === 200 && response.data) {
                    commit(SET_REPORT, response.data)
                } else {
                    commit(SET_REPORT)
                }
            })
        },
        [ SAVE_REPORT ] ({dispatch}, report) {
            /*
                Update the existing reports table and Remove the current report from the store
             */
            let handleSuccess = () => {
                dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 })
                dispatch(FETCH_REPORT)
            }

            if (report.uuid && report.uuid !== 'new') {
                return dispatch(REQUEST_API, {
                    rule: `reports/${report.uuid}`,
                    method: 'POST',
                    data: report
                }).then((response) => {
                    if (response.status === 200) {
                        return handleSuccess()
                    }
                })
            } else {
                return dispatch(REQUEST_API, {
                    rule: 'reports',
                    method: 'PUT',
                    data: report
                }).then((response) => {
                    if (response.status === 201 && response.data) {
                        handleSuccess()
                        return response.data
                    }
                })
            }
        },
        [ REMOVE_REPORTS ] ({dispatch}, selection) {
            /*
                Remove given selection of Report.
                Expected structure is a list of ids and a flag indicating whether to include or exclude them
             */
            return dispatch(REQUEST_API, {
                rule: 'reports',
                method: 'DELETE',
                data: selection
            }).then((response) => {
                if (response.status === 200) {
                    dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 })
                }
            })
        },
        [ RUN_REPORT ] ({dispatch}, report) {
            /*
                run the report
             */
            let handleSuccess = (id) => {
                dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 })
                dispatch(FETCH_REPORT, id)
            }

                return dispatch(REQUEST_API, {
                    rule: `test_exec_report`,
                    method: 'POST',
                    data: report
                }).then((response) => {
                    if (response.status === 200) {
                        return handleSuccess(report.uuid)
                    }
                })

        },
        [ DOWNLOAD_REPORT ] ({dispatch}, { reportId, name } ) {
            return dispatch(REQUEST_API, {
                rule: `export_report/${reportId}`,
                binary: true
            }).then((response) => {
                downloadPdfReportFile(name, response)
            })
        }
    }
}