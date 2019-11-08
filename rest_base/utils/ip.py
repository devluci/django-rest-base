from typing import Union, Optional

from django.http import HttpRequest
from rest_framework.request import Request

from rest_base.settings import base_settings

__all__ = ['get_client_ip']


def get_client_ip(request: Union[HttpRequest, Request]) -> Optional[str]:
    meta = request.META

    for key in base_settings.IP_HEADERS:
        ip: str = meta.get(key)
        if ip:
            if ',' in ip:
                return ip.split(',')[0].strip()
            return ip
