import secrets
from abc import ABC
from inspect import isclass
from math import ceil
from typing import Type, Callable, Any, Dict

from django.db import ProgrammingError, OperationalError
from django.db.models import Model, Field

from rest_base.settings import base_settings
from rest_base.utils.registry import ModuleRegistry

__all__ = [
    'initialize_base_fields', 'PredefinedDefault',
    'UniqueRandom',
    'UniqueRandomInt', 'UniqueRandomPositiveInt32', 'UniqueRandomPositiveInt52', 'UniqueRandomPositiveInt64',
    'UniqueRandomChar',
]


def not_found():
    return None


unique_random = ModuleRegistry('unique_random', default=not_found)


class PredefinedDefault(ABC):
    def __init__(self):
        raise ProgrammingError(f'{self.__class__.__name__} must not be initialized')

    @classmethod
    def get_default_func(cls, model: Type[Model], field: Field) -> Callable[[], Any]:
        raise NotImplementedError('get_default_func must be defined')


class UniqueRandom(PredefinedDefault, ABC):
    pass


class UniqueRandomInt(UniqueRandom):
    """
    Unique random default int in the range [min_val, max_val)
    """

    min_val = None
    max_val = None

    @classmethod
    def get_default_func(cls, model: Type[Model], field: Field) -> Callable[[], int]:
        min_val = cls.min_val
        max_val = cls.max_val

        if min_val is None:
            raise NotImplementedError(f'{cls.__name__}.min_val must be provided')
        if max_val is None:
            raise NotImplementedError(f'{cls.__name__}.max_val must be provided')
        if type(min_val) is not int:
            raise TypeError(f'{cls.__name__}.min_val must be int but value is {min_val}')
        if type(max_val) is not int:
            raise TypeError(f'{cls.__name__}.max_val must be int but value is {max_val}')

        val_gap = max_val - min_val
        field_name = field.name
        max_collision_check = base_settings.MAX_UNIQUE_COLLISION_CHECK

        if val_gap < 1:
            raise ValueError(f'{cls.__name__}.max_val - {cls.__name__}.min_val must be bigger than 0')

        def _random():
            val = None
            try:
                for _ in range(max_collision_check):
                    val = secrets.randbelow(val_gap) - min_val
                    if not model.objects.filter(**{field_name: val}).exists():
                        return val
            except ProgrammingError:
                return val
            raise OperationalError(f'Cannot find unique value of {model.__name__}.{field_name}')

        return _random


class UniqueRandomPositiveInt(UniqueRandomInt):
    min_val = 0


class UniqueRandomPositiveInt32(UniqueRandomPositiveInt):
    max_val = 1 << 31


class UniqueRandomPositiveInt52(UniqueRandomPositiveInt):
    max_val = 1 << 51


class UniqueRandomPositiveInt64(UniqueRandomPositiveInt):
    max_val = 1 << 63


class UniqueRandomChar(UniqueRandom):
    """
    Unique random default max_len url-safe characters
    """

    @classmethod
    def get_default_func(cls, model: Type[Model], field: Field) -> Callable[[], int]:
        field_name = field.name
        length = field.max_length
        max_collision_check = base_settings.MAX_UNIQUE_COLLISION_CHECK

        if type(length) is not int:
            raise TypeError(
                f'{model.__name__}.{field_name} must have integer max_length but value is {length}')

        val_len = ceil(length * 3 / 4)

        def _random():
            val = None
            try:
                for _ in range(max_collision_check):
                    val = secrets.token_urlsafe(val_len)[:length]
                    if not model.objects.filter(**{field_name: val}).exists():
                        return val
            except ProgrammingError:
                return val
            raise OperationalError(f'Cannot find unique value of {model.__name__}.{field_name}')

        return _random


def initialize_base_fields(model: Type[Model], attrs: Dict[str, Any]) -> Type[Model]:
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    for field_name, field in attrs.items():
        if not isinstance(field, Field):
            continue

        field: Field
        if field.is_relation and field.remote_field.related_name is None:
            raise ValueError(
                f"{model_name}.{field_name}.related_name must be explicitly provided."
                f"You can set '+' to omit backwards relation."
            )

        default = field.default
        if not isclass(default) or not issubclass(default, PredefinedDefault):
            continue

        default: Type[PredefinedDefault]
        if issubclass(default, UniqueRandom) and not field.unique:
            raise ValueError(f'{model_name}.{field_name}.unique must be True to use UniqueRandom')

        func_name = f'{app_label}_{model_name}_{default}'
        default_func = default.get_default_func(model, field)

        unique_random[func_name] = default_func
        field.default = default_func

    return model
