import os

from django.core.management.commands.startapp import Command as StartAppCommand

import rest_base


class Command(StartAppCommand):
    def handle(self, **options):
        if options['template'] is None:
            options['template'] = os.path.join(rest_base.__path__[0], 'conf/app_template')

        super().handle(**options)
