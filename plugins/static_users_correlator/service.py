from axonius.correlator_base import CorrelatorBase
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file

from static_users_correlator.engine import StaticUserCorrelatorEngine


class StaticUsersCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        self._correlation_engine = StaticUserCorrelatorEngine()

    def _correlate(self, entities: list):
        return self._correlation_engine.correlate(entities)

    @property
    def _entity_to_correlate(self) -> EntityType:
        return EntityType.Users
