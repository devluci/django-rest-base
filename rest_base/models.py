from __future__ import annotations

import sys
from math import log10
from typing import Optional, Iterable, TypeVar, List, Tuple, Dict, Any, Type

from django import db
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager as DjangoBaseUserManager
from django.db import models, DatabaseError, transaction
from django.db.models.expressions import RawSQL, F
from django.db.transaction import Atomic
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_base.fields import UniqueRandomPositiveInt32, UniqueRandomChar, initialize_base_fields
from rest_base.settings import base_settings

__all__ = [
    'BaseQuerySet', 'BaseManager',
    'BulkUpdateQuerySet', 'BulkUpdateManager',
    'BaseModel', 'AlreadyLocked', 'semaphore',
    'BaseUserManager', 'BaseUser', 'BaseToken',
]

Instance = TypeVar('Instance', bound=models.Model)


class BaseQuerySet(models.QuerySet):
    def update_or_create(self, defaults: Dict[str, Any] = None, **kwargs):
        defaults = defaults or dict()
        self._for_write = True
        with transaction.atomic(using=self.db):
            try:
                obj = self.select_for_update().get(**kwargs)
            except self.model.DoesNotExist:
                params = self._extract_model_params(defaults, **kwargs)
                obj, created = self._create_object_from_params(kwargs, params, lock=True)
                if created:
                    return obj, created
            modified = set()
            for k, v in defaults.items():
                try:
                    old_v = getattr(obj, k)
                except AttributeError:
                    continue
                v = v() if callable(v) else v
                if old_v != v:
                    setattr(obj, k, v)
                    modified.add(k)
            if modified:
                obj.save(update_fields=modified, using=self.db)
        return obj, False


class BaseManager(models.Manager):
    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db, hints=self._hints)


class BulkUpdateQuerySet(models.QuerySet):
    def bulk_create(
            self, objs: Iterable[Instance],
            batch_size: Optional[int] = base_settings.DB_BATCH_SIZE, ignore_conflicts: bool = False
    ) -> List[Instance]:
        self._for_write = True
        return models.QuerySet(self.model, using=self.db).bulk_create(objs, batch_size, ignore_conflicts)

    def update(self, **kwargs) -> int:
        self._for_write = True
        select_query_set = self.order_by('pk').values('pk')
        return models.QuerySet(self.model, using=self.db).filter(pk__in=RawSQL(
            str(select_query_set.query) + ' FOR NO KEY UPDATE', ()
        )).update(**kwargs)
    update.alters_data = True

    def bulk_update(
            self, objs: Iterable[Instance], fields: Iterable[str],
            batch_size: Optional[int] = base_settings.DB_BATCH_SIZE
    ):
        if not objs:
            return

        self._for_write = True
        pks = [obj.pk for obj in objs]
        query_set = self.filter(pk__in=pks).order_by('pk')
        with transaction.atomic():
            with db.connection.cursor() as cursor:
                cursor.execute(str(query_set.query) + ' FOR NO KEY UPDATE', ())
            return models.QuerySet(self.model, using=self.db).bulk_update(objs, fields, batch_size)
    bulk_update.alters_data = True

    def delete(self) -> Tuple[int, Dict[str, int]]:
        self._for_write = True
        query_set = self.order_by('pk').values('pk')
        return models.QuerySet(self.model, using=self.db).filter(pk__in=RawSQL(
            str(query_set.query) + ' FOR UPDATE', ()
        )).delete()
    delete.alters_data = True
    delete.queryset_only = True


class BulkUpdateManager(models.Manager):
    def get_queryset(self):
        return BulkUpdateQuerySet(self.model, using=self._db, hints=self._hints)


class BaseModelMeta(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        abstract = getattr(attrs.get('Meta', None), 'abstract', False)
        new_class = super().__new__(cls, name, bases, attrs, **kwargs)
        if not abstract:
            initialize_base_fields(new_class)
        return new_class


class BaseModel(models.Model, metaclass=BaseModelMeta):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_modified = models.DateTimeField(auto_now=True, db_index=True)

    objects = BaseManager()
    bulk_manager = BulkUpdateManager()

    class Meta:
        abstract = True

    def save(
            self, force_insert: bool = False, force_update: bool = False, using: str = None,
            update_fields: Iterable[str] = None
    ):
        if not self._state.adding and update_fields is not None:
            if type(update_fields) is not list:
                update_fields = list(update_fields)
            update_fields.append('last_modified')
        super().save(force_insert, force_update, using, update_fields)
    save.alters_data = True


class AlreadyLocked(Exception):
    def __init__(self, instance):
        self.instance = instance

    def __str__(self):
        return f'AlreadyLocked ({self.instance})'


def semaphore(*, block: bool):
    nowait = not block

    def decorator(cls: Type[models.Model]):
        class Model(cls):
            def __enter__(self: models.Model):
                self._atomic: Atomic = transaction.atomic()
                self._atomic.__enter__()
                try:
                    self.__class__.objects.select_for_update(nowait=nowait).get(pk=self.pk)
                except DatabaseError:
                    self._atomic.__exit__(*sys.exc_info())
                    raise AlreadyLocked(self)

            def __exit__(self, exc_type, exc_val, exc_tb):
                return self._atomic.__exit__(exc_type, exc_val, exc_tb)

        return Model

    return decorator


class BaseUserManager(BaseManager, DjangoBaseUserManager):
    def create_user(self, username: str, password: str):
        user = self.model(username=username)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username: str, password: str):
        user = self.create_user(username, password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user


class BaseUser(BaseModel, AbstractBaseUser, PermissionsMixin):
    user_id = models.PositiveIntegerField(primary_key=True, default=UniqueRandomPositiveInt32)
    username = models.CharField(max_length=base_settings.USERNAME_LENGTH_MAX, unique=True, default=None, null=True, blank=True)
    password = models.CharField(_('password'), max_length=base_settings.PASSWORD_LENGTH_MAX, default='', blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_guest = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'

    objects = BaseUserManager()

    class Meta:
        abstract = True

    class DeactivatedUser(Exception):
        def __init__(self, user: BaseUser):
            self._user = user

    def __str__(self):
        return self.username

    def raise_for_deactivation(self):
        if not self.is_active:
            raise BaseUser.DeactivatedUser(self)


class BaseToken(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tokens')
    public_key = models.CharField(max_length=40, unique=True, default=UniqueRandomChar)
    secret_key = models.CharField(max_length=40, unique=True, default=UniqueRandomChar)
    duration = models.DurationField()
    nonce = models.CharField(
        max_length=int(log10(base_settings.NONCE_MAX) + 1) * base_settings.NONCE_WINDOW_SIZE, default='', blank=True)

    class Meta:
        abstract = True

    class TokenMeta:
        duration = base_settings.DEFAULT_TOKEN_DURATION

    class NonceError(Exception):
        pass

    def __str__(self):
        return f'{self.__class__.__name__} ({self.user})'

    @classmethod
    def new(cls, user: BaseUser, duration: timezone.timedelta = None, **kwargs) -> BaseToken:
        user.raise_for_deactivation()

        if duration is None:
            duration = cls.TokenMeta.duration
        token = cls.objects.create(user=user, duration=duration, **kwargs)

        return token

    @classmethod
    def get(cls, public_key: str, next_nonce: int = None, include_user: bool = True) -> Optional[BaseToken]:
        if not public_key:
            return None

        try:
            if include_user:
                queryset = cls.objects.select_related('user')
            else:
                queryset = cls.objects

            token: cls = queryset.get(
                public_key=public_key,
                last_modified__gt=timezone.now() - F('duration'),
                user__is_active=True,
            )

            if next_nonce is None:
                token.save(update_fields=[])
            else:
                if not 0 <= next_nonce < base_settings.NONCE_MAX:
                    return None

                if not token.nonce:
                    token.nonce = str(next_nonce)
                else:
                    nonce_list = [int(n) for n in token.nonce.split(';')]

                    if next_nonce in nonce_list:
                        return None
                    if next_nonce < nonce_list[0]:
                        return None

                    nonce_list.append(next_nonce)
                    nonce_list = sorted(nonce_list)[-base_settings.NONCE_WINDOW_SIZE:]

                    token.nonce = ';'.join(str(n) for n in nonce_list)

                token.save(update_fields=['nonce'])

            return token
        except cls.DoesNotExist:
            return None
