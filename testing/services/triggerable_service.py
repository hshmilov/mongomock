from abc import ABC, abstractmethod


class TriggerableService(ABC):
    @property
    @abstractmethod
    def api_key(self):
        pass

    def triggerable_execute_enable(self, *vargs, **kwargs):
        return getattr(self, 'post')('trigger_activate/execute', api_key=self.api_key, *vargs, **kwargs)

    def triggerable_execute_disable(self, *vargs, **kwargs):
        return getattr(self, 'post')('trigger_deactivate/execute', api_key=self.api_key, *vargs, **kwargs)

    def triggerable_execute(self, *vargs, **kwargs):
        return getattr(self, 'post')('trigger/execute', api_key=self.api_key, *vargs, **kwargs)

    def triggerable_get_state(self, *vargs, **kwargs):
        return getattr(self, 'get')('state', api_key=self.api_key, *vargs, **kwargs)
