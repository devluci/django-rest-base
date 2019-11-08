from typing import Type

from django import urls
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.db.models.fields import related
from django.forms import ModelForm, ModelMultipleChoiceField
from django.utils.html import escape
from django.utils.safestring import mark_safe

from rest_base.models import BaseModel, BaseToken, BaseUser
from rest_base.settings import base_settings

__all__ = ['model_admin']

User: Type[BaseUser] = get_user_model()


NULL = base_settings.ADMIN_NULL_STRING
MAX_FOREIGN_OBJECT_PREVIEW = base_settings.MAX_FOREIGN_OBJECT_PREVIEW


def _get_link_method(field: related.ForeignKey):
    field_name = field.name
    foreign_model = field.remote_field.model

    def link_method(self, instance):
        foreign_instance = getattr(instance, field_name)
        if foreign_instance is None:
            return NULL

        href = urls.reverse(
            f'admin:{foreign_model._meta.app_label.lower()}_{foreign_model._meta.object_name.lower()}_change',
            args=[foreign_instance.pk],
        )
        instance_str = escape(str(foreign_instance))

        return mark_safe(f'<a href="{href}" target="_blank">{instance_str}</a>')

    link_method.__name__ = field.name

    return link_method


def _get_multiple_link_method(field: related.ManyToManyField):
    field_name = field.name
    foreign_model = field.remote_field.model

    def link_method(self, instance):
        link_list = []
        for foreign_instance in getattr(instance, field_name).all()[:MAX_FOREIGN_OBJECT_PREVIEW]:
            href = urls.reverse(
                f'admin:{foreign_model._meta.app_label.lower()}_{foreign_model._meta.object_name.lower()}_change',
                args=[foreign_instance.pk],
            )
            instance_str = escape(str(foreign_instance))

            link_list.append(f'<a href="{href}" target="_blank">{instance_str}</a>')

        if not link_list:
            return NULL

        return mark_safe('<br>'.join(link_list))

    link_method.__name__ = field.name

    return link_method


def model_admin(model: Type[models.Model], search_fields: list = None):
    primary_key_display = []
    autocomplete_fields = []
    if search_fields is None:
        search_fields = []

    list_display = []
    list_display_sub = []
    list_display_link = dict()

    base_fields = set(f.name for f in BaseModel._meta.fields)

    for field in model._meta.fields:
        if not primary_key_display and field.primary_key:
            primary_key_display = [field.name]
            search_fields.append(field.name)
        elif field.get_internal_type() == 'ForeignKey' or field.get_internal_type() == 'OneToOneField':
            autocomplete_fields.append(field.name)
            list_display.append(field.name + '_link')
            list_display_link[field.name + '_link'] = _get_link_method(field)
        elif field.name in base_fields:
            list_display_sub.append(field.name)
        else:
            list_display.append(field.name)

    for field in model._meta.many_to_many:
        list_display.append(field.name + '_link')
        list_display_link[field.name + '_link'] = _get_multiple_link_method(field)

    return model, type(
        model.__name__ + 'Admin',
        (admin.ModelAdmin,),
        dict(
            search_fields=search_fields,
            autocomplete_fields=autocomplete_fields,

            list_display=primary_key_display + list_display + list_display_sub,
            **list_display_link
        )
    )


class GroupAdminForm(ModelForm):
    class Meta:
        model = Group
        exclude = []

    users = ModelMultipleChoiceField(
         queryset=User.objects.all(),
         required=False,
         widget=FilteredSelectMultiple('users', False)
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['users'].initial = self.instance.user_set.all()

    def _save_m2m(self):
        super()._save_m2m()
        self.instance.user_set.set(self.cleaned_data['users'])


class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    list_display = ['name', 'permissions_list', 'users']
    filter_horizontal = ['permissions']

    search_fields = ['name']

    def permissions_list(self, instance):
        link_list = []
        for foreign_instance in instance.permissions.all()[:MAX_FOREIGN_OBJECT_PREVIEW]:
            link_list.append(escape(str(foreign_instance)))
        if not link_list:
            return NULL
        return mark_safe('<br>'.join(link_list))
    permissions_list.__name__ = 'permissions'

    def users(self, instance):
        link_list = []
        for user in instance.user_set.all()[:MAX_FOREIGN_OBJECT_PREVIEW]:
            href = urls.reverse(
                f'admin:{User._meta.app_label.lower()}_{User._meta.object_name.lower()}_change',
                args=[user.pk],
            )
            user_str = escape(str(user))

            link_list.append(f'<a href="{href}" target="_blank">{user_str}</a>')

        if not link_list:
            return NULL
        return mark_safe('<br>'.join(link_list))


admin.site.register(*model_admin(BaseToken, ['user__user_id', 'user__username']))

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
