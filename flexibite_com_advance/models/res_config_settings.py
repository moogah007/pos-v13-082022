#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
import ast

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def load_rfid_settings(self):
        record = {}
        settings_is_rfid_login = self.env['ir.config_parameter'].sudo().search([('key', '=', 'is_rfid_login')])
        if settings_is_rfid_login:
            record['is_rfid_login'] = settings_is_rfid_login.value
            return [record]

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res_user_ids = param_obj.sudo().get_param('res_user_ids')
        if res_user_ids:
            res.update({'res_user_ids': ast.literal_eval(res_user_ids)})

        res.update(
            theme_selector=param_obj.get_param('theme_selector'),
            gen_barcode=param_obj.get_param('gen_barcode'),
            barcode_selection=param_obj.get_param('barcode_selection'),
            gen_internal_ref=param_obj.get_param('gen_internal_ref'),
            mailsend_check=param_obj.get_param('mailsend_check'),
            email_notification_days=int(param_obj.sudo().get_param('email_notification_days')),
            is_rfid_login=param_obj.get_param('is_rfid_login'),
            kitchen_screen_timer=param_obj.get_param('kitchen_screen_timer'),
            bday_tmpl_id=int(param_obj.sudo().get_param('bday_tmpl_id'))
            if param_obj.sudo().get_param('bday_tmpl_id') else False,
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.set_param('theme_selector', self.theme_selector or False)
        param_obj.set_param('gen_barcode', self.gen_barcode)
        param_obj.set_param('barcode_selection', self.barcode_selection)
        param_obj.set_param('gen_internal_ref', self.gen_internal_ref)
        param_obj.set_param('mailsend_check', self.mailsend_check)
        param_obj.set_param('res_user_ids', self.res_user_ids.ids)
        param_obj.set_param('email_notification_days', self.email_notification_days)
        param_obj.set_param('is_rfid_login', self.is_rfid_login or False)
        param_obj.set_param('bday_tmpl_id', self.bday_tmpl_id and self.bday_tmpl_id.id or False)
        param_obj.set_param('kitchen_screen_timer', self.kitchen_screen_timer or False)
        return res

    @api.model
    def load_settings(self, fields):
        res_config_settings = self.env['res.config.settings'].sudo().search_read([], [fields], order='id desc', limit=1,
                                                                                 offset=0)
        return res_config_settings or False

    kitchen_screen_timer = fields.Boolean(string="Timer In Kitchen Screen")
    theme_selector = fields.Selection(
        [('green_orange', 'Green Orange'), ('blue_yellow', 'Blue Yellow'),
         ('purple_blue', 'Purple Blue'), ('dark_theme', 'Dark Theme'), ('multi_color', 'Restaurant'),
         ('black_yellow', 'Black Yellow')])
    gen_barcode = fields.Boolean("On Product Create Generate Barcode")
    barcode_selection = fields.Selection([('code_39', 'CODE 39'), ('code_128', 'CODE 128'),
                                          ('ean_13', 'EAN-13'), ('ean_8', 'EAN-8'),
                                          ('isbn_13', 'ISBN 13'), ('isbn_10', 'ISBN 10'),
                                          ('issn', 'ISSN'), ('upca', 'UPC-A')], string="Select Barcode Type")
    gen_internal_ref = fields.Boolean(string="On Product Create Generate Internal Reference")
    mailsend_check = fields.Boolean(string="Send Mail")
    email_notification_days = fields.Integer(string="Expiry Alert Days")
    res_user_ids = fields.Many2many('res.users', string='Users')
    is_rfid_login = fields.Boolean("RFID Pos Login")
    bday_tmpl_id = fields.Many2one('mail.template', string="Birthday Template",
                                   domain="[('model', '=','res.partner')]")
    last_token_number = fields.Char(string="Last Token Number")


class res_company(models.Model):
    _inherit = "res.company"

    pos_price = fields.Char(string="Pos Price", size=1)
    pos_quantity = fields.Char(string="Pos Quantity", size=1)
    pos_discount = fields.Char(string="Pos Discount", size=1)
    pos_search = fields.Char(string="Pos Search", size=1)
    pos_next = fields.Char(string="Pos Next order", size=1)
    payment_total = fields.Char(string="Payment", size=1)
    report_ip_address = fields.Char(string="Thermal Printer Proxy IP")
    store_ids = fields.Many2many("pos.store", 'pos_store_company_rel', 'store_id', 'company_id', string='Allow Stores')

    # @api.one
    def write(self, vals):
        current_store_ids = self.store_ids
        res = super(res_company, self).write(vals)
        if 'store_ids' in vals:
            current_store_ids -= self.store_ids
            for store in current_store_ids:
                store.company_id = False
            for store in self.store_ids:
                store.company_id = self
        return res


class res_partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def loyalty_reminder(self):
        partner_ids = self.search([('email', "!=", False), ('send_loyalty_mail', '=', True)])
        for partner_id in partner_ids.filtered(lambda partner: partner.remaining_loyalty_points > 0):
            try:
                template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
                                                                             'email_template_loyalty_reminder')
                template_obj = self.env['mail.template'].browse(template_id[1])
                template_obj.send_mail(partner_id.id, force_send=True, raise_exception=False)
            except Exception as e:
                _logger.error('Unable to send email for order %s', e)

    # @api.multi
    def _calculate_earned_loyalty_points(self):
        loyalty_point_obj = self.env['loyalty.point']
        for partner in self:
            total_earned_points = 0.00
            for earned_loyalty in loyalty_point_obj.search([('partner_id', '=', partner.id)]):
                total_earned_points += earned_loyalty.points
            partner.loyalty_points_earned = total_earned_points

    # @api.multi
    def _calculate_remaining_loyalty(self):
        loyalty_point_obj = self.env['loyalty.point']
        loyalty_point_redeem_obj = self.env['loyalty.point.redeem']
        for partner in self:
            points_earned = 0.00
            amount_earned = 0.00
            points_redeemed = 0.00
            amount_redeemed = 0.00
            for earned_loyalty in loyalty_point_obj.search([('partner_id', '=', partner.id)]):
                points_earned += earned_loyalty.points
                amount_earned += earned_loyalty.amount_total
            for redeemed_loyalty in loyalty_point_redeem_obj.search([('partner_id', '=', partner.id)]):
                points_redeemed += redeemed_loyalty.redeemed_point
                amount_redeemed += redeemed_loyalty.redeemed_amount_total
            partner.remaining_loyalty_points = points_earned - points_redeemed
            partner.remaining_loyalty_amount = amount_earned - amount_redeemed
            partner.total_remaining_points = points_earned - points_redeemed

    #             partner.sudo().write({
    #                 'total_remaining_points': points_earned - points_redeemed
    #             })

    wallet_acount_move_line_ids = fields.One2many('account.move.line', 'partner_id')
    loyalty_points_earned = fields.Float(compute='_calculate_earned_loyalty_points')
    wallet_balance = fields.Float('Wallet Balance', compute='_calculate_wallet_balance')
    remaining_loyalty_points = fields.Float("Remaining Loyalty Points", readonly=1,
                                            compute='_calculate_remaining_loyalty')
    remaining_loyalty_amount = fields.Float("Points to Amount", readonly=1, compute='_calculate_remaining_loyalty')
    send_loyalty_mail = fields.Boolean("Send Loyalty Mail", default=True)
    total_remaining_points = fields.Float("Total Loyalty Points", readonly=1, compute='_calculate_remaining_loyalty')

    def get_wallet_balance_domain(self, partner):
        return [
            ('partner_id', '=', self._find_accounting_partner(partner).id),
            ('reconciled', '=', False),
            ('is_wallet', '=', True),
        ]

    def _calculate_wallet_balance(self):
        for partner in self:
            total_balance = 0.0
            account_data = self.env['account.move.line'].search(self.get_wallet_balance_domain(partner))
            total_balance += sum(account_data.mapped('balance'))
            partner.wallet_balance = total_balance

    def wallet_account_lines(self):
        for partner in self:
            partner_id = partner.id
        wallet_account_line = self.env.ref('flexibite_com_advance.wallet_account_line_tree_view').id
        return {
            'name': _('Wallet Account Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'views': [(wallet_account_line, 'tree'), (False, 'form')],
            'view_id': wallet_account_line,
            'domain': self.get_wallet_balance_domain(self),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
