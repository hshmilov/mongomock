from abc import ABC, abstractmethod


class ActivateableService(ABC):
    @property
    @abstractmethod
    def api_key(self):
        pass

    def activateable_start(self, *vargs, **kwargs):
        return getattr(self, 'post')('start', api_key=self.api_key, *vargs, **kwargs)

    def activateable_stop(self, *vargs, **kwargs):
        return getattr(self, 'post')('stop', api_key=self.api_key, *vargs, **kwargs)

    def activateable_get_state(self, *vargs, **kwargs):
        return getattr(self, 'get')('state', api_key=self.api_key, *vargs, **kwargs)
