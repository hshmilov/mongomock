from datetime import datetime
from enum import auto, Enum
from typing import List, Optional, Iterable

from bson import ObjectId
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from axonius.entities import EntityType


@dataclass(frozen=True)
class AlertActionResult(DataClassJsonMixin):
    # Whether or not the execution was successful
    successful: bool
    # Execution result
    status: object


@dataclass(frozen=True)
class EntityResult(DataClassJsonMixin):
    # The internal axon id this refers to
    internal_axon_id: str
    # Whether or not the execution was successful
    successful: bool
    # Execution result
    status: object


# This represents each entity in the results of an execution of an action
EntitiesResult = Iterable[EntityResult]


# This is the result of an action that was ran
@dataclass(frozen=True)
class ActionRunResults(DataClassJsonMixin):
    # List of internal_axon_ids of all entities the action has succeeded upon
    successful_entities: EntitiesResult
    # List of internal_axon_ids of all entities the action has failed upon
    unsuccessful_entities: EntitiesResult
    # If the action has raised an exception is will appear here
    exception_state: str


# This is the result of an action that was ran as it will be saved in the DB
@dataclass(frozen=True)
class DBActionRunResults(DataClassJsonMixin):
    # See ActionRunResults and EntitiesResult
    successful_entities: ObjectId
    # See ActionRunResults and EntitiesResult
    unsuccessful_entities: ObjectId
    # If the action has raised an exception is will appear here,
    # otherwise it will have the first of the EntityResults' status, which will be primarily used
    # by the GUI for alert actions
    message_state: str


class SavedActionType(Enum):
    """
    The type of the saved action
    """
    action = 'action'
    alert = 'alert'


@dataclass
class SavedActionData(DataClassJsonMixin):
    # For regular actions, look at inheritors of ActionTypeBase in action_types/*
    # For trigger summary actions, look at inheritors of ActionTypeAlert in action_types/*
    action_name: str
    # The config that will be passed (self._config in ActionTypeBase)
    config: object
    # The type of the action.
    # This should be SavedActionType, but enum works so bad with dataclasses, I won't bother fixing this up
    action_type: Optional[str] = None
    # This will represent the action results in the DB, where applicable
    results: Optional[ActionRunResults] = None


# This is how actions will look inside a recipe
@dataclass
class ActionInRecipe(DataClassJsonMixin):
    # The name of the saved action
    name: str
    # The action it represents
    action: SavedActionData


class TriggeredReason(Enum):
    """
    Defines the various reasons a trigger may be triggered
    """

    manual = 'Manual run'
    every_discovery = 'Any results'
    new_entities = 'New entities were added'
    previous_entities = 'Previous entities were removed'
    above = 'The number of entities is above {}'
    below = 'The number of entities is below {}'


@dataclass(frozen=True)
class TriggerView(DataClassJsonMixin):
    # The name of the saved query to be used
    name: str
    # The entity type of the saved query
    entity: EntityType


@dataclass(frozen=True)
class TriggerConditions(DataClassJsonMixin):
    # If new entities were added to the query, since last time
    new_entities: Optional[bool]
    # If entities were subtracted from the query, since last time
    previous_entities: Optional[bool]
    # If the amount of entities is above this
    above: Optional[int]
    # If the amount of entities is below this
    below: Optional[int]


class TriggerPeriod(Enum):
    """
    Defines various periods for triggers
    """

    # pylint: disable=E0213
    def _generate_next_value_(name, *args):
        return name

    # every cycle
    all = 'Every Discovery Cycle'
    daily = 'Daily'
    weekly = 'Weekly'
    monthly = 'Monthly'
    never = 'Manually only'


class RunOnEntities(Enum):
    """
    Defines which entities the enforcement should run upon
    """

    # pylint: disable=E0213
    def _generate_next_value_(name, *args):
        return name

    AllEntities = auto()
    # Run just on the entities that were added to the query
    AddedEntities = auto()


@dataclass
class Trigger(DataClassJsonMixin):
    # The name of the trigger (unique per enforcement)
    name: str
    # Details of the view to base trigger on
    view: TriggerView
    # Running conditions: None implies that this will always run
    conditions: TriggerConditions
    # How often should this run
    period: TriggerPeriod
    # The last time this configuration has ran
    last_triggered: datetime
    # Foreign reference to the list of internal axon ids that the query has yielded last time
    result: ObjectId
    # Result count
    result_count: int
    # Amount of times the trigger validated
    times_triggered: int
    # Which entities to run upon
    run_on: RunOnEntities

    @staticmethod
    def from_dict(to_parse) -> 'Trigger':
        return Trigger(
            name=to_parse['name'],
            view=TriggerView(to_parse['view']['name'], EntityType(to_parse['view']['entity'])),
            conditions=TriggerConditions.schema().make_triggerconditions(to_parse['conditions']),
            period=TriggerPeriod[to_parse['period']],
            last_triggered=to_parse.get('last_triggered'),
            result=to_parse.get('result'),
            result_count=to_parse.get('result_count'),
            times_triggered=to_parse.get('times_triggered', 0),
            run_on=RunOnEntities(to_parse['run_on'])
        )


# This is the metadata for a run of a recipe
@dataclass()
class RecipeRunMetadata(DataClassJsonMixin):
    # The trigger used for this run
    trigger: Trigger
    # Set of reasons why this was triggered, see ReportsService._get_triggered_reports
    triggered_reason: List[str]
    # Total succeeded / total run for the Main action
    success_rate: float
    # A nice number generated so the GUI won't display ugly IDs
    pretty_id: Optional[int] = None


# This is the recipe of an alert. It does not include stuff like the name, query or trigger.
@dataclass(frozen=True)
class Recipe(DataClassJsonMixin):
    # The main action that runs first
    main: Optional[ActionInRecipe]
    # These actions will run only on entities that are reported by the main action as "success"
    success: List[ActionInRecipe]
    # These actions will run only on entities that are reported by the main action as "failed"
    failure: List[ActionInRecipe]
    # These actions will run only on all entities, after the main action
    post: List[ActionInRecipe]
    # This will represent the recipe run metadata, for the "triggerable_history" - i.e. the results of the
    # run of the recipe
    metadata: Optional[RecipeRunMetadata] = None
