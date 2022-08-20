# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

import logging
from odoo import models, fields, api, _
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def calculate_partner(self):
        partner_ids = self.search([])
        if partner_ids:
            return partner_ids.ids
        else:
            return []

    # @api.multi
    def _calc_credit_dbt_remaining(self):
        print("\n\n _calc_credit_dbt_remaining====> ")
        # for partner in self:
        #     data = self.env['account.invoice'].get_outstanding_info(partner.id)
        #     amount = []
        #     amount_data = 0.00
        #     total = 0.00
        #     for pay in data['content']:
        #         amount_data = pay['amount']
        #         amount.append(amount_data)
        #     for each_amount in amount:
        #         total += each_amount
        #     partner.remaining_credit_amount = total

    @api.model
    def create_from_ui(self, partner):
        if partner.get('property_product_pricelist'):
            price_list_id = int(partner.get('property_product_pricelist'))
            partner.update({'property_product_pricelist': price_list_id})
        return super(ResPartner, self).create_from_ui(partner)

    # @api.multi
    def _compute_remain_credit_limit(self):
        for partner in self:
            total_credited = 0
            orders = self.env['pos.order'].search([('partner_id', '=', partner.id),
                                                   ('state', '=', 'draft')])
            for order in orders:
                total_credited += order.amount_due
            partner.remaining_credit_limit = partner.credit_limit - total_credited

    # @api.multi
    def _calc_debit_remaining(self):
        for partner in self:
            pos_orders = self.env['pos.order'].search([('partner_id', '=', partner.id), ('state', '=', 'draft')
                                                          , ('reserved', '=', False)])
            amount = sum([order.amount_due for order in pos_orders]) or 0.00
            partner.remaining_debit_amount = partner.debit_limit - amount

    # @api.multi
    @api.depends('used_ids', 'recharged_ids')
    def compute_amount(self):
        total_amount = 0
        for ids in self:
            for card_id in ids.card_ids:
                total_amount += card_id.card_value
            ids.remaining_amount = total_amount

    # @api.one
    @api.depends('wallet_lines')
    def _calc_remaining(self):
        total = 0.00
        for s in self:
            for line in s.wallet_lines:
                total += line.credit - line.debit
        self.remaining_wallet_amount = total

    @api.model
    def customer_greetings(self):
        today = date.today()
        partner = self.search([('email', "!=", False)])
        birthday_tmpl = self.env['ir.config_parameter'].sudo().get_param('bday_tmpl_id')
        anniversary_tmpl = self.env['ir.config_parameter'].sudo().get_param('anniversary_tmpl_id')

        if partner:
            for each in partner:
                if each.birth_date == today:
                    try:
                        template_obj = self.env['mail.template'].browse(int(birthday_tmpl))
                        template_obj.send_mail(each.id, force_send=True, raise_exception=False)

                    except Exception as e:
                        _logger.error('Unable to send email for birthday %s', e)

    card_ids = fields.One2many('aspl.gift.card', 'customer_id', string="List of card")
    exchange_history_ids = fields.One2many('aspl.gift.card.exchange.history', 'customer_id')
    used_ids = fields.One2many('aspl.gift.card.use', 'customer_id', string="List of used card")
    recharged_ids = fields.One2many('aspl.gift.card.recharge', 'customer_id', string="List of recharged card")
    remaining_amount = fields.Char(compute=compute_amount, string="GiftCard Amount", readonly=True)

    wallet_lines = fields.One2many('wallet.management', 'customer_id', string="Wallet", readonly=True)
    remaining_wallet_amount = fields.Float(compute="_calc_remaining", string="Remaining Amount", readonly=True,
                                           store=True)
    prefer_ereceipt = fields.Boolean('Prefer E-Receipt')
    remaining_credit_limit = fields.Float("Remaining Reservation Credit Limit", compute="_compute_remain_credit_limit")
    remaining_credit_amount = fields.Float(compute="_calc_credit_dbt_remaining", string="Credit Amount",
                                           store=True, readonly=True)
    debit_limit = fields.Float("Debit Limit")
    remaining_debit_amount = fields.Float(compute="_calc_debit_remaining", string="Remaining Debit Limit",
                                          readonly=True)
    birth_date = fields.Date("Birth Date")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
