from __future__ import annotations

import traceback
from typing import TypedDict, Literal, Optional, Union

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, Http404
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


sentry_enabled = bool(base_settings.SENTRY_HOST)
sentry_verbose = base_settings.SENTRY_VERBOSE

if sentry_enabled:
    try:
        import sentry_sdk
    except ImportError:
        sentry_sdk = None
else:
    sentry_sdk = None


class Error(APIException):
    status_code = status.HTTP_400_BAD_REQUEST

    class SerializedCode(TypedDict):
        code: str

    class SerializedDetail(SerializedCode, total=False):
        detail: str
        traceback: str

    class Serialized(TypedDict):
        error: Error.SerializedDetail

    def __init__(
            self, app_or_request: Union[str, HttpRequest, Request],
            *args: str, code: str = None, detail: str = None, tb: str = None, status_code: int = None,
    ):
        if type(app_or_request) is str:
            self.app = app_or_request
        elif isinstance(app_or_request, HttpRequest):
            self.app = app_or_request.resolver_match.app_name
        elif isinstance(app_or_request, Request):
            self.app = app_or_request.resolver_match.app_name
        else:
            raise ValueError(
                f'app_or_request must be str, HttpRequest, or Request but {type(app_or_request)} provided')

        self.code = code or '::'.join(args) or CODE_UNKNOWN
        self.serialized: Error.Serialized = Error.Serialized(
            error=dict(
                code=self.code,
            ),
        )
        if detail is not None:
            self.serialized['error']['detail'] = detail
        if tb is not None:
            self.serialized['error']['traceback'] = tb
        if status_code is not None:
            self.status_code = status_code

        super().__init__(self.serialized, self.code)

    def __str__(self):
        return f'Error ({self.code})'

    def __call__(self, *args, code: str = None, detail: str = None, tb: str = None) -> Error:
        code = code or '::'.join(args) or self.code
        return Error(self.app, code=code, detail=detail, tb=tb)


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
