from abc import ABC, abstractmethod


class ActivateableService(ABC):
    @property
    @abstractmethod
    def api_key(self):
        pass

    def activateable_start(self, *kargs, **kwargs):
        return getattr(self, 'get')('start', api_key=self.api_key, *kargs, **kwargs)

    def activateable_stop(self, *kargs, **kwargs):
        return getattr(self, 'get')('stop', api_key=self.api_key, *kargs, **kwargs)

    def activateable_get_state(self, *kargs, **kwargs):
        return getattr(self, 'get')('state', api_key=self.api_key, *kargs, **kwargs)
