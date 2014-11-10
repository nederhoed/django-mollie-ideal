#-*- coding: utf-8 -*-

import os, urllib
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from mollie.ideal.settings import MOLLIE_API_URL


class Command(BaseCommand):
    help = 'Fetches the latest list of supported banks from Mollie.nl'
    requires_model_validation = False
    option_list = BaseCommand.option_list + (
        make_option(
            '--testmode',
            action='store_true',
            dest='testmode',
            default=False,
            help=("Fetch the list in testmode. This gets the test "
                  "bank 'TBM Bank' (The Big Mollie Bank).")),
        make_option(
            '-t',
            '--target',
            dest='target_dir',
            default='',
            help=("Target dir for the XML file. For example `--target=/tmp/`")),
        )

    def handle(self, *args, **options):
        testmode = options['testmode']
        here = options['target_dir'] or os.path.realpath('.')
        url = '%s?a=banklist' % MOLLIE_API_URL
        if testmode:
            url += '&testmode=true'
        file = os.path.join(here, 'mollie_banklist.xml')
        try:
            urllib.urlretrieve(url, file)
            print 'File %s saved to %s.' % (os.path.basename(file), here)
        except:
            raise CommandError('Something went wrong!')
