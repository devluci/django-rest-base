from __future__ import annotations

import traceback
from typing import TypedDict, Literal, Optional, Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, Http404
from django.utils.functional import cached_property
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import exception_handler as rest_exception_handler

from rest_base.settings import base_settings

__all__ = [
    'SENTRY_ERROR_LEVEL', 'CODE_UNKNOWN',
    'Error', 'sentry_report', 'ExceptionHandlerContext', 'exception_handler',
]

SENTRY_ERROR_LEVEL = Literal['debug', 'info', 'warning', 'error', 'fatal']
CODE_UNKNOWN = 'Unknown'

sentry_enabled = bool(getattr(base_settings, 'SENTRY_HOST', False))
sentry_verbose = getattr(base_settings, 'SENTRY_VERBOSE', False)

if sentry_enabled:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(base_settings.SENTRY_HOST, integrations=[sentry_sdk.integrations.django.DjangoIntegration()])
    except ImportError:
        sentry_sdk = None
        DjangoIntegration = None
else:
    sentry_sdk = None
    DjangoIntegration = None


class Error(APIException):
    app: Optional[str] = None
    code: Optional[str] = None
    str_detail: Optional[str] = None
    extra: Optional[Any] = None
    traceback: Optional[str] = None
    status_code: int = status.HTTP_400_BAD_REQUEST

    class SerializedCode(TypedDict):
        code: str

    class SerializedDetail(SerializedCode, total=False):
        detail: str
        extra: Any
        traceback: str

    class Serialized(TypedDict):
        error: Error.SerializedDetail

    def __new__(
            cls, *args, code: str = None, str_detail: str = None, extra: Any = None,
            tb: str = None, status_code: int = None,
    ):
        if cls.app is None:
            if not args:
                raise ValueError('app_name, Request or HttpRequest must be provided as first argument')

            app_or_request = args[0]
            if type(app_or_request) is str:
                app = app_or_request
            elif isinstance(app_or_request, HttpRequest):
                app = app_or_request.resolver_match.app_name
            elif isinstance(app_or_request, Request):
                app = app_or_request.resolver_match.app_name
            else:
                raise ValueError(
                    f'str, HttpRequest, or Request expected as first argument, but {type(app_or_request)} provided')

            if len(args) == 1 and code is None:
                code = CODE_UNKNOWN
                name = app.title().replace('_', '') + 'Error'
            else:
                code = code or '::'.join(args[1:]) or CODE_UNKNOWN
                name = code.replace('::', '')
        else:
            if not args and code is None:
                return super().__new__(cls)

            app = cls.app
            code = code or '::'.join(args) or CODE_UNKNOWN
            name = code.replace('::', '')

        _app, _code, _str_detail, _extra, _status_code = app, code, str_detail, extra, status_code

        class SubError(cls):
            app = _app.lower()
            code = _code
            str_detail = _str_detail or cls.str_detail
            extra = _extra or cls.extra
            traceback = tb or cls.traceback
            status_code = _status_code or cls.status_code
        SubError.__name__ = name
        SubError.__qualname__ = name

        return SubError

    def __init__(
            self, *args, code: str = None, detail: str = None, extra: Any = None,
            tb: str = None, status_code: int = None,
    ):
        if detail is not None:
            self.detail = detail
        if extra is not None:
            self.extra = extra
        if tb is not None:
            self.traceback = tb
        if status_code is not None:
            self.status_code = status_code

        super().__init__(self.serialized, self.code)

    def __str__(self):
        return f'Error ({self._app}::{self._code})'

    def __call__(self, *args, code: str = None, detail: str = None, extra: Any = None, tb: str = None) -> Error:
        return Error(self._app, *args, code=code, detail=detail, extra=extra, tb=tb)

    @cached_property
    def serialized(self) -> Error.Serialized:
        serialized: Error.Serialized = Error.Serialized(
            error=Error.SerializedDetail(code=self.code)
        )

        if self.str_detail is not None:
            serialized['error']['detail'] = self.str_detail
        if self.extra is not None:
            serialized['error']['extra'] = self.extra
        if self.traceback is not None:
            serialized['error']['traceback'] = self.traceback

        return serialized


def sentry_report(
        exc: Exception, level: SENTRY_ERROR_LEVEL = 'error', silent: bool = True
) -> Optional[int]:
    global sentry_enabled, sentry_verbose

    if not sentry_enabled:
        if not silent:
            raise RuntimeError('SENTRY_HOST is not found from django.conf.settings')
        return

    if sentry_sdk is None:
        if not silent:
            raise ImportError('Module sentry_sdk is not found. Try `pip install django-rest-base[sentry]`.')
        return

    if level in ('debug', 'info') and not sentry_verbose:
        return

    with sentry_sdk.configure_scope() as scope:
        scope.set_level(level)
        try:
            return sentry_sdk.capture_exception(exc)
        except Exception as e:
            print('sentry error:', e)
            print(traceback.format_exc())
            if not silent:
                raise


class ExceptionHandlerContext(TypedDict):
    view: APIView
    args: tuple
    kwargs: dict
    request: Request


def exception_handler(exc: Exception, context: ExceptionHandlerContext) -> Optional[Response]:
    if isinstance(exc, Error):
        sentry_report(exc, level='debug')

        if settings.DEBUG:
            if context['request'].content_type.startswith('application/json'):
                exc = exc(traceback=traceback.format_exc())
            else:
                return None
    elif isinstance(exc, APIException):
        sentry_report(exc, level='debug')
        exc = Error(context['request'], exc.__class__.__name__, detail=exc.detail, status_code=exc.status_code)
    elif not isinstance(exc, (Http404, PermissionDenied)):
        event_id = sentry_report(exc)
        event_id = f'event_id: {event_id}' if event_id is not None else None

        if settings.DEBUG:
            return None
        else:
            exc = Error(context['request'], detail=event_id)

    return rest_exception_handler(exc, context)
