from typing import Callable, Union, Iterable, Type, Sequence, Optional

from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

__all__ = ['method_branch']


def _perform_authentication(self, request: Request):
    pass


APIView.perform_authentication = _perform_authentication


def _authenticate(authenticators: Union[None, Iterable[Type[BaseAuthentication]]], request: Request):
    if not authenticators:
        return

    for authenticator in authenticators:
        user_auth_tuple = authenticator().authenticate(request)
        if user_auth_tuple is not None:
            return user_auth_tuple


def _authentication_header(
        authentications: Union[None, Sequence[Type[BaseAuthentication]]], request: Request
) -> Optional[str]:
    if authentications:
        return authentications[0]().authenticate_header(request)


def _check_permissions(
        permissions: Union[None, Iterable[Type[BasePermission]]], request: Request, view: APIView
) -> bool:
    if not permissions:
        return True

    for permission in permissions:
        if not permission().has_permission(request, view):
            return False

    return True


def method_branch(
        *,
        GET: Callable[..., Response] = None,
        POST: Callable[..., Response] = None,
        PUT: Callable[..., Response] = None,
        DELETE: Callable[..., Response] = None,
):
    methods = list()

    default_authentications = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    default_permissions = api_settings.DEFAULT_PERMISSION_CLASSES

    get_authentications = post_authentications = put_authentications = delete_authentications = None
    get_permissions = post_permissions = put_permissions = delete_permissions = None
    if GET is not None:
        methods.append('GET')
        get_authentications = getattr(GET, 'authentication_classes', default_authentications)
        get_permissions = getattr(GET, 'permission_classes', default_permissions)
    if POST is not None:
        methods.append('POST')
        post_authentications = getattr(POST, 'authentication_classes', default_authentications)
        post_permissions = getattr(POST, 'permission_classes', default_permissions)
    if PUT is not None:
        methods.append('PUT')
        put_authentications = getattr(PUT, 'authentication_classes', default_authentications)
        put_permissions = getattr(PUT, 'permission_classes', default_permissions)
    if DELETE is not None:
        methods.append('DELETE')
        delete_authentications = getattr(DELETE, 'authentication_classes', default_authentications)
        delete_permissions = getattr(DELETE, 'permission_classes', default_permissions)

    class AuthenticationClass(BaseAuthentication):
        def authenticate(self, request: Request):
            if request.method == 'GET':
                return _authenticate(get_authentications, request)
            if request.method == 'POST':
                return _authenticate(post_authentications, request)
            if request.method == 'PUT':
                return _authenticate(put_authentications, request)
            if request.method == 'DELETE':
                return _authenticate(delete_authentications, request)

        def authenticate_header(self, request: Request) -> Optional[str]:
            if request.method == 'GET':
                return _authentication_header(get_authentications, request)
            if request.method == 'POST':
                return _authentication_header(post_authentications, request)
            if request.method == 'PUT':
                return _authentication_header(put_authentications, request)
            if request.method == 'DELETE':
                return _authentication_header(delete_authentications, request)

    class PermissionClass(BasePermission):
        def has_permission(self, request: Request, view: APIView):
            if request.method == 'GET':
                return _check_permissions(get_permissions, request, view)
            if request.method == 'POST':
                return _check_permissions(post_permissions, request, view)
            if request.method == 'PUT':
                return _check_permissions(put_permissions, request, view)
            if request.method == 'DELETE':
                return _check_permissions(delete_permissions, request, view)
            return True

    @api_view(methods)
    @permission_classes((PermissionClass,))
    @authentication_classes((AuthenticationClass,))
    def branch(request: Request, *args, **kwargs):
        if request.method == 'GET':
            return GET(request, *args, **kwargs)
        if request.method == 'POST':
            return POST(request, *args, **kwargs)
        if request.method == 'PUT':
            return PUT(request, *args, **kwargs)
        if request.method == 'DELETE':
            return DELETE(request, *args, **kwargs)

    return branch
