import { REQUEST_API, downloadFile } from '../actions'

export const DOWNLOAD_REPORT = 'DOWNLOAD_REPORT'
export const reports = {
	state: {},
	actions: {
		[ DOWNLOAD_REPORT ] ({dispatch}) {
			return dispatch(REQUEST_API, {
				rule: 'export_report',
				binary: true
			}).then((response) => {
                downloadFile('pdf', response)
            })
		}
	}
}