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

from odoo import models, api, fields, _
from datetime import datetime
from odoo.addons.account.wizard.pos_box import CashBox


# class account_journal(models.Model):
#     _inherit = "account.journal"
#
#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         if self._context.get('config_jr'):
#             if self._context.get('journal_ids') and \
#                     self._context.get('journal_ids')[0] and \
#                     self._context.get('journal_ids')[0][2]:
#                 args += [['id', 'in', self._context.get('journal_ids')[0][2]]]
#             else:
#                 return False;
#         if self._context.get('from_delivery'):
#             args += [['jr_use_for', '=', False]]
#         return super(account_journal, self).name_search(name, args=args, operator=operator, limit=limit)
#
#     shortcut_key = fields.Char('Shortcut Key')
#     jr_use_for = fields.Selection([
#         ('loyalty', "Loyalty"),
#         ('gift_card', "Gift Card"),
#         ('gift_voucher', "Gift Voucher"),
#         ('rounding', "Rounding"),
#         ('credit', "Credit")
#     ], string="Method Use For",
#         help='This payment method reserve for particular feature, that accounting entry will manage based on assigned features.')
#     # apply_charges = fields.Boolean("Apply Charges");
#     # fees_amount = fields.Float("Fees Amount");
#     # fees_type = fields.Selection(selection=[('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Fees type",
#     #                              default="fixed")
#     # optional = fields.Boolean("Optional")


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # @api.one
    @api.constrains('amount')
    def _check_amount(self):
        if not self._context.get('from_pos'):
            super(AccountBankStatementLine, self)._check_amount()

    # @api.one
    @api.constrains('amount', 'amount_currency')
    def _check_amount_currency(self):
        if not self._context.get('from_pos'):
            super(AccountBankStatementLine, self)._check_amount_currency()

    is_money_in = fields.Boolean("Is Money In");
    is_money_out = fields.Boolean("Is Money Out");


# class CashBoxIn(CashBox):
#     _inherit = 'cash.box.in'
#
#     # @api.multi
#     def _calculate_values_for_statement_line(self, record):
#         res = super(CashBoxIn, self)._calculate_values_for_statement_line(record)
#         if res:
#             res.update({
#                 'is_money_in': True
#             })
#         return res


class CashBoxOut(CashBox):
    _inherit = 'cash.box.out'

    # @api.multi
    def _calculate_values_for_statement_line(self, record):
        res = super(CashBoxOut, self)._calculate_values_for_statement_line(record)
        if res:
            res.update({
                'is_money_out': True
            })
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_wallet = fields.Boolean("Is Wallet")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
