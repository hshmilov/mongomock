import { REQUEST_API } from '../actions'

export const DOWNLOAD_REPORT = 'DOWNLOAD_REPORT'
export const report = {
	state: {},
	actions: {
		[ DOWNLOAD_REPORT ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'export_report',
				binary: true
			})
		}
	}
}