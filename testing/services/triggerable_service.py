from abc import ABC, abstractmethod


class TriggerableServiceMixin(ABC):
    @property
    @abstractmethod
    def api_key(self):
        pass

    def triggerable_execute(self, *vargs, **kwargs):
        return self.post('trigger/execute', api_key=self.api_key, *vargs, **kwargs)

    def triggerable_get_state(self, *vargs, **kwargs):
        return self.get('state', api_key=self.api_key, *vargs, **kwargs)
