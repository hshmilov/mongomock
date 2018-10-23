from services.plugin_service import PluginService


class ReportsService(PluginService):
    def __init__(self):
        super().__init__('reports')

    def _migrade_db(self):
        super()._migrade_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()

    @staticmethod
    def __update_schema_version_1(collection):
        for report_data in collection.find():
            triggers = report_data['triggers']
            new_triggers = {}
            new_triggers['every_discovery'] = bool(triggers.get('no_change'))
            new_triggers['new_entities'] = bool(triggers.get('increase') and not triggers.get('above'))
            new_triggers['previous_entities'] = bool(triggers.get('decrease') and not triggers.get('below'))
            new_triggers['above'] = triggers.get('above', 0)
            new_triggers['below'] = triggers.get('below', 0)

            report_data['triggers'] = new_triggers
            collection.replace_one({'_id': report_data['_id']}, report_data)

    def _update_schema_version_1(self):
        print('upgrade to schema 1')
        try:
            db = self.db.client
            for x in [x for x in db.database_names() if x.startswith('reports_')]:
                self.__update_schema_version_1(collection=db[x]['reports'])
            self.db_schema_version = 1
        except Exception as e:
            print(f'Could not upgrade reports db to version 1. Details: {e}')

    def _request_watches(self, method, *vargs, **kwargs):
        return getattr(self, method)('reports', api_key=self.api_key, *vargs, **kwargs)

    def get_watches(self, *vargs, **kwargs):
        return self._request_watches('get', *vargs, **kwargs)

    def create_watch(self, data, *vargs, **kwargs):
        return self._request_watches('put', data=data, *vargs, **kwargs)

    def delete_watch(self, data, *vargs, **kwargs):
        return self._request_watches('delete', data=data, *vargs, **kwargs)

    def run_jobs(self):
        self.get('trigger_reports', api_key=self.api_key)
