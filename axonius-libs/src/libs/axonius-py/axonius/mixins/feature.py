from abc import ABC, abstractclassmethod

import itertools


class Feature(ABC):
    """
    Defines a class that implements a feature that will be also returned in /supported_features
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._supported_features = self.__supported_features()

    @classmethod
    def __recurse_tree(cls, recurse_type):
        """
        Recurse into all base classes to get all supported_features
        :param recurse_type:
        :return:
        """
        for base in recurse_type.__bases__:
            if base is object or base is Feature:
                continue
            if hasattr(base, 'supported_features'):
                yield from base.specific_supported_features()
            yield from cls.__recurse_tree(base)

    @classmethod
    def __supported_features(cls):
        """
        Calculates all the features of the current class by recursing into all base classes
        :return:
        """
        return set(itertools.chain(cls.specific_supported_features() or [], cls.__recurse_tree(cls)))

    @property
    def supported_features(self):
        """
        The features of the current class
        :return:
        """
        return self._supported_features

    # noinspection PyMethodParameters
    @abstractclassmethod
    def specific_supported_features(cls) -> list:
        """
        Return the features this plugin adds
        """
