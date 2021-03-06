# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from mollie.ideal.helpers import _get_mollie_xml, get_mollie_bank_choices

logger = logging.getLogger('mollie.ideal')


class MollieIdealPayment(models.Model):

    transaction_id = models.CharField(_('Transaction ID'), max_length=255)
    amount = models.DecimalField(_('Amount'), max_digits=64, decimal_places=2)
    bank_id = models.CharField(_('Bank ID'), max_length=4,
                               choices=get_mollie_bank_choices(show_all_banks=True),
                               default = '')
    description = models.CharField(_('Description'), max_length=29)
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    consumer_account = models.CharField(_('Consumer account'), max_length=255, blank=True)
    consumer_name = models.CharField(_('Consumer name'), max_length=255, blank=True)
    consumer_city = models.CharField(_('Consumer city'), max_length=255, blank=True)

    class Meta:
        abstract = True
        verbose_name = _('Mollie/iDEAL payment')

    def get_order_url(self, reporturl=None, returnurl=None):
        'Sets up a payment with Mollie.nl and returns an order URL.'
        if settings.MOLLIE_REVERSE_URLS:
            if reporturl is None:
                reporturl = settings.MOLLIE_SITE_FULL_URL + reverse(
                    settings.MOLLIE_REPORT_URL)
            if returnurl is None:
                returnurl = settings.MOLLIE_SITE_FULL_URL + reverse(
                    settings.MOLLIE_RETURN_URL)
        else:
            if reporturl is None:
                reporturl = settings.MOLLIE_REPORT_URL
            if returnurl is None:
                returnurl = settings.MOLLIE_RETURN_URL
        request_dict = dict(
            a = 'fetch',
            amount = int(self.amount * 100),
            bank_id = self.bank_id,
            description = self.description,
            partnerid = settings.MOLLIE_PARTNER_ID,
            reporturl = reporturl,
            returnurl = returnurl
        )
        if settings.MOLLIE_PROFILE_KEY:
            request_dict.update(dict(
                profile_key=settings.MOLLIE_PROFILE_KEY
            ))
        parsed_xml = _get_mollie_xml(request_dict)
        order = parsed_xml.find('order')
        if order is None:
            logger.error("No order found in xml.")
            # Most likely the reporturl points to localhost, which is
            # an error.
            error = parsed_xml.findtext('error') or 'unknown'
            if 'localhost' in reporturl or '127.0.0.1' in reporturl:
                raise ValueError("reporturl must not point to localhost. "
                                 "It must be reachable by mollie.nl.")
            raise ValueError("No order found. Error: %s" % (error,))
        order_url = order.findtext('URL')
        self.transaction_id = order.findtext('transaction_id')
        self.save()
        return order_url

    fetch = get_order_url
        
    def is_paid(self):
        'Checks whether a payment has been made successfully.'
        request_dict = dict(
            a = 'check',
            partnerid = settings.MOLLIE_PARTNER_ID,
            transaction_id = self.transaction_id
        )
        parsed_xml = _get_mollie_xml(request_dict)
        order = parsed_xml.find('order')
        if order is None:
            logger.error("No order found in xml for transaction id %s.",
                         self.transaction_id)
            # Most likely the reporturl or returnurl points to
            # localhost, which is an error.
            raise ValueError("No order found.")
        consumer = order.find('consumer')
        if consumer:
            self.consumer_account = consumer.findtext('consumerAccount')
            self.consumer_city = consumer.findtext('consumerCity')
            self.consumer_name = consumer.findtext('consumerName')
        if order.findtext('payed') == 'true':
            logger.info("Transaction %s is paid.", self.transaction_id)
            return True
        message = order.findtext('message')
        logger.error("Transaction id %s not paid. Message: %s",
                     self.transaction_id, message)
        status = order.findtext('status')
        if status:
            logger.error("Transaction id %s not paid. Status: %s",
                         self.transaction_id, status)
        return False

    check = is_paid

    @property
    def bank_name(self):
        return self.get_bank_id_display()

    def __unicode__(self):
        return u'Mollie/iDEAL Payment ID: %d' % self.id
