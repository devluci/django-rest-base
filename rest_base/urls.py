from typing import Callable

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings

__all__ = ['method_branch']


def method_branch(
        *,
        GET: Callable[..., Response] = None,
        POST: Callable[..., Response] = None,
        PUT: Callable[..., Response] = None,
        DELETE: Callable[..., Response] = None,
):
    methods = list()
    get_permissions, post_permissions, put_permissions, delete_permissions = None, None, None, None
    if GET is not None:
        methods.append('GET')
        get_permissions = getattr(GET, 'permission_classes', api_settings.DEFAULT_PERMISSION_CLASSES)
        get_permissions = [permission() for permission in get_permissions]
    if POST is not None:
        methods.append('POST')
        post_permissions = getattr(POST, 'permission_classes', api_settings.DEFAULT_PERMISSION_CLASSES)
        post_permissions = [permission() for permission in post_permissions]
    if PUT is not None:
        methods.append('PUT')
        put_permissions = getattr(PUT, 'permission_classes', api_settings.DEFAULT_PERMISSION_CLASSES)
        put_permissions = [permission() for permission in put_permissions]
    if DELETE is not None:
        methods.append('DELETE')
        delete_permissions = getattr(DELETE, 'permission_classes', api_settings.DEFAULT_PERMISSION_CLASSES)
        delete_permissions = [permission() for permission in delete_permissions]

    class PermissionClass(BasePermission):
        def has_permission(self, request, view):
            if request.method == 'GET':
                if get_permissions is None:
                    return True
                for permission in get_permissions:
                    if not permission.has_permission(request, view):
                        return False
                return True
            if request.method == 'POST':
                if post_permissions is None:
                    return True
                for permission in post_permissions:
                    if not permission.has_permission(request, view):
                        return False
                return True
            if request.method == 'PUT':
                if put_permissions is None:
                    return True
                for permission in put_permissions:
                    if not permission.has_permission(request, view):
                        return False
                return True
            if request.method == 'DELETE':
                if delete_permissions is None:
                    return True
                for permission in delete_permissions:
                    if not permission.has_permission(request, view):
                        return False
                return True
            return True

    def branch(request: Request, *args, **kwargs):
        if request.method == 'GET':
            return GET(request, *args, **kwargs)
        if request.method == 'POST':
            return POST(request, *args, **kwargs)
        if request.method == 'PUT':
            return PUT(request, *args, **kwargs)
        if request.method == 'DELETE':
            return DELETE(request, *args, **kwargs)

    return api_view(methods)(permission_classes((PermissionClass,))(branch))
