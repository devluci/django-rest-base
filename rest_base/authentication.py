from typing import Type

from django.conf import settings
from django.utils.datastructures import MultiValueDict
from rest_framework.authentication import BaseAuthentication, get_authorization_header, SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .models import BaseToken
from .settings import base_settings

try:
    import jwt
except ImportError:
    jwt = None

__all__ = ['CsrfExemptSessionAuthentication', 'TokenAuthentication']


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request: Request):
        return


class TokenAuthentication(BaseAuthentication):
    AUTHORIZATION_PREFIX = 'Bearer'
    AUTHORIZATION_PREFIX_BYTES = AUTHORIZATION_PREFIX.encode()

    model: Type[BaseToken] = base_settings.AUTHENTICATION_MODEL

    def __init__(self, *args, **kwargs):
        if jwt is None:
            raise ImportError(
                'PyJWT must be installed to use TokenAuthentication. Try `pip install django-rest-base[jwt]`.')
        if not isinstance(self.model, BaseToken):
            raise RuntimeError(
                f'BaseToken must be provided to either settings.REST_BASE.AUTHENTICATION_MODEL '
                f'or {self.__class__.__name__}.model'
            )

        super().__init__(*args, **kwargs)

    def authenticate(self, request: Request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0] != TokenAuthentication.AUTHORIZATION_PREFIX_BYTES:
            return None

        if len(auth) != 2:
            raise AuthenticationFailed(detail='Invalid Bearer format.')

        try:
            jwt_payload = auth[1].decode()
        except UnicodeError:
            raise AuthenticationFailed(detail='Invalid Bearer encoding type.')

        header = jwt.get_unverified_header(jwt_payload)
        public_key = header.get('public_key')
        nonce = header.get('nonce')

        try:
            nonce = int(nonce)
        except ValueError:
            raise AuthenticationFailed(detail='Invalid nonce.')

        token = self.model.get(public_key, nonce)
        if token is None:
            raise AuthenticationFailed(detail='Invalid public_key or nonce.')

        try:
            payload = jwt.decode(jwt_payload, token.secret_key, algorithms='HS256')
        except jwt.exceptions.InvalidTokenError as e:
            if settings.DEBUG:
                raise AuthenticationFailed(detail=f'Invalid JWT: {e}')
            else:
                raise AuthenticationFailed(detail='Invalid JWT.')

        query = payload.get('query')
        if query:
            query_params = request.query_params
            data = request.data
            if isinstance(query_params, MultiValueDict):
                query_params = query_params.dict()
            if isinstance(data, MultiValueDict):
                data = data.dict()

            if (not data and query == query_params) or (not query_params and query == data):
                return token.user, token
        else:
            if not request.query_params and not request.data:
                return token.user, token

        raise AuthenticationFailed(detail='Query not match.')

    def authenticate_header(self, request):
        return TokenAuthentication.AUTHORIZATION_PREFIX
