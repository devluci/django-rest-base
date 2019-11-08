# Django REST base

**Customized features and environment for building a Django REST framework app.**



# Requirements

- Python 3.8
- Django 3.0
- djangorestframework (Django REST framework)

Optional packages required for additional features.

- PyJWT `TokenAuthentication`
- channels `NullURLRouter`, `NullConsumer`
- sentry-sdk `sentry_report` (when [Sentry](https://sentry.io/) reports enabled)
- numpy `rest_base.utils.random`



# Installation

```shell script
pip install django-rest-base
```

#### `settings.py`
```python
INSTALLED_APPS = [
    ...,
    'rest_base',
]
```



# Features

## Error
#### `settings.py`
```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'rest_base.errors.exception_handler',
}
```

#### `errors.py`
```python
from rest_base.errors import Error

my_app = Error('my_app')

MY_ERROR = my_app('My', 'Error')
```

#### `views.py`
```python
from my_app.errors import MY_ERROR

def my_view(request):
    raise MY_ERROR(detail='Something went wrong :(')
```

`rest_base.errors.exception_handler` is similar with REST framework's default handler, but provides advanced error format.

In Django REST base environment, every exception from views inherits `rest_base.errors.Error`. Even original REST framework's exceptions and unhandled exceptions will be converted to `Error`.

Those `Error`s will generate `Response` which has following error format.
```json
{
  "error": {
    "code": "My::Error",
    "detail": "Something went wrong :(",
    "traceback": "(traceback)"
  }
}
```

`detail` and `traceback` are optional, and `traceback` will be included automatically when Django's DEBUG mode is enabled.



## View
#### `urls.py`
```python
from django.urls import re_path

from rest_base.urls import method_branch
from . import views

urlpatterns = [
    re_path(r'^my_endpoint/?$', method_branch(GET=views.my_view, POST=views.another_view)),
]
```

`rest_base.urls.method_branch` branch the requests by it's method—`GET`, `POST`, `PUT`, `DELETE`.
It also supports `@rest_framework.decorators.permission_classes` for each view.



## Model
#### `models.py`
```python
from rest_base.models import BaseModel, BaseUser, BaseToken, semaphore

@semaphore(block=True)
class MyModel(BaseModel):
    field = ...

class MyUser(BaseUser):
    field = ...

class MyToken(BaseToken):
    field = ...
```

By replacing the original Django `models.Model` with `rest_base.models.BaseModel`, several customized features can be used.
- `created`, `last_modified` fields
- `objects.update_or_create` only updates instance when original attributes and provided `defaults` are not same.
- `bulk_manager`
    - Supports deadlock free following methods. (PostgreSQL ONLY)
    - `update`, `bulk_update`, `delete`
- `PredefinedDefault` (See [Fields](#fields) for more)
- `related_name` must be provided when field's type is `ForeignKey`, `OneToOneField` or `ManyToManyField`.

You can use customized `BaseUser` and JWT based `BaseToken` by inherit it.
See [Authentication](#authentication) for more information about JWT authentication.

## Fields
#### `models.py`
```python
from django.db import models

from rest_base.fields import UniqueRandomPositiveInt32
from rest_base.models import BaseModel

class MyModel(BaseModel):
    unique_field = models.IntegerField(unique=True, default=UniqueRandomPositiveInt32)
```

If your model inherits `rest_base.models.BaseModel`, you can set the default value as
- `UniqueRandomPositiveInt32`
- `UniqueRandomPositiveInt52`
- `UniqueRandomPositiveInt64`
- `UniqueRandomChar` (unique random url-safe characters)

Then default value will be replaced with unique random value in the run-time.



## Admin
#### `admin.py`
```python
from django.contrib import admin

from rest_base.admin import model_admin
from .models import *

admin.site.register(*model_admin(MyModel))
```

You can easily register you models to Django admin page by using `rest_base.admin.model_admin`.
It registers all of the model's fields and supports link to `ForeignKey`, `OneToOneField` and `ManyToManyField` on Django admin.



## Authentication
```shell script
pip install django-rest-base[jwt]
```

#### `models.py`
```python
from rest_base.models import BaseToken

class Token(BaseToken):
    pass
```

#### `settings.py`
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_base.authentication.CsrfExemptSessionAuthentication',
        'rest_base.authentication.TokenAuthentication',
    ),
}

REST_BASE = {
    'AUTHENTICATION_MODEL': 'my_app.models.Token',
}
```

#### `views.py`
```python
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated


@permission_classes((IsAuthenticated,))
def my_view(request):
    ...
```

Each `Token` which inherits `BaseToken` has `public_key` and `secret_key`.
You can make bearer using following format.
```json
// Header
{
  "alg": "HS256",
  "typ": "JWT",
  "public_key": "public_key",
  "nonce": 31
}
// Payload
{
  "query": {
    "key": "value"
  }
}
```

Then set the HTTP Authorization header to
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInB1YmxpY19rZXkiOiJwdWJsaWNfa2V5Iiwibm9uY2UiOjMxfQ.eyJxdWVyeSI6eyJrZXkiOiJ2YWx1ZSJ9fQ.q1849tjsSspbtyBYHxsmS98FLUIG2W97aj_gaCxWGlg
```

Remember that nonce must be a positive int32 value which increases for each request.



## Sentry
```shell script
pip install django-rest-base[sentry]
```

#### `settings.py`
```python
REST_BASE = {
    'SENTRY_HOST': 'https://<key>@sentry.io/<project>',
    'SENTRY_VERBOSE': False,  # report handled exceptions, default False
}
```

If `sentry-sdk` installed, `SENTRY_HOST` provided and `rest_base.errors.exception_handler` configured correctly,
every unhandled exception from view will be reported to the Sentry.

Handled exceptions also reported if you set `SENTRY_VERBOSE` to `True`.



## Channels
```shell script
pip install django-rest-base[channels]
```

#### `routing.py`
```python
from django.urls import path
from rest_base.routing import NullURLRouter

websocket_urlpatterns = [
    path('app/', NullURLRouter(my_app.routing.websocket_urlpatterns)),
]
```



## Etc
- By default, startapp command will use template in `rest_base/conf/app_template` which contains additional code for Django REST base
- .env can be loaded by
```python
from rest_base.utils import dotenv

dotenv.load('path/to/.env')
```
- You can dump/load predefined model instances by using
```shell script
python manage.py dump my_app.Model
python manage.py load my_app.Model
```



# License

[MIT](./LICENSE)
