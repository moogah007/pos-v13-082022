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

import pytz
import logging
import ast
import psycopg2
from odoo import models, fields, api, tools, _
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.account.wizard.pos_box import CashBox
from pytz import timezone
from odoo.tools import float_is_zero
from odoo import SUPERUSER_ID
from operator import itemgetter
from timeit import itertools
from functools import partial
from collections import defaultdict

_logger = logging.getLogger(__name__)


def start_end_date_global(start, end, tz):
    tz = pytz.timezone(tz) or 'UTC'
    current_time = datetime.now(tz)
    hour_tz = int(str(current_time)[-5:][:2])
    min_tz = int(str(current_time)[-5:][3:])
    sign = str(current_time)[-6][:1]
    sdate = start + " 00:00:00"
    edate = end + " 23:59:59"
    if sign == '-':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    if sign == '+':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    return start_date, end_date


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if (self._context.get('store_ids')):
            store_ids = self.env['pos.store'].browse(self._context.get('store_ids')[0][2])
            config_ids = []
            for store in store_ids:
                config_ids.append(store.config_id.id)
            args += [('id', 'in', config_ids)]
            res = super(PosConfig, self).name_search(name, args=args, operator=operator, limit=limit)
            return res
        else:
            res = super(PosConfig, self).name_search(name, args=args, operator=operator, limit=limit)
            return res

    @api.model
    def set_default_customer(self, config_id, partner_id):
        sql = """UPDATE pos_config SET 
                        default_partner_id = %s 
                        WHERE id = %s
                  """ % (partner_id, config_id)
        self._cr.execute(sql)
        return True

    @api.constrains('time_interval', 'prod_qty_limit')
    def _check_time_interval(self):
        if self.enable_automatic_lock and self.time_interval < 0:
            raise Warning(_('Time Interval Not Valid'))
        if self.prod_qty_limit < 0:
            raise Warning(_('Restrict product quantity must not be negative'))

    # @api.multi
    # def write(self, vals):
    #     if vals.get('module_pos_restaurant'):
    #         raise Warning(_("You Can't Use Restaurant While Using Flexibite!"))
    #     res = super(PosConfig, self).write(vals)
    #     return res

    # @api.model
    # def create(self, values):
    #     if values.get('module_pos_restaurant'):
    #         raise Warning(_("You Can't Use Restaurant While Using Flexibite!"))
    #     res = super(PosConfig, self).create(values)
    #     return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        user_rec = self.env['res.users'].browse(self._uid)
        erp_manager_id = self.env['ir.model.data'].get_object_reference('base',
                                                                        'group_erp_manager')[1]
        lst = []
        if user_rec and erp_manager_id not in user_rec.groups_id.ids:
            if user_rec.store_ids:
                for each in user_rec.store_ids:
                    if each.config_id:
                        lst.append(each.config_id.id)
                domain = [('id', 'in', lst)]
        return super(PosConfig, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit,
                                                  order=order)

    pos_dashboard = fields.Boolean(string="Sales Dashboard")
    login_screen = fields.Boolean("Login Screen")
    enable_ereceipt = fields.Boolean('Send E-Receipt')
    enable_quick_cash_payment = fields.Boolean(string="Quick Cash Payment")
    validate_on_click = fields.Boolean(string="Validate On Click")
    cash_method = fields.Many2one('pos.payment.method', "Cash Payment Method")
    payment_buttons = fields.Many2many(comodel_name='quick.cash.payment',
                                       relation='amount_button_name',
                                       column1='payment_amt_id', column2='pos_config_id')
    enable_order_note = fields.Boolean('Order Note')
    enable_product_note = fields.Boolean('Product / Line Note')
    enable_pos_return = fields.Boolean("Return Order/Products")
    enable_reorder = fields.Boolean("Reorder")
    last_days = fields.Char("Last Days")
    enable_draft_order = fields.Boolean("Draft Order")
    generate_token = fields.Boolean(string="Generate Token")
    seperate_receipt = fields.Boolean(string="Seperate Receipt")
    mrp_operation_type = fields.Many2one('stock.picking.type', string="MRP Operation Type")
    enable_manufacturing = fields.Boolean('Enable Manufacturing')
    change_bom = fields.Boolean('Change Bom')
    generate_mo_after_payment = fields.Boolean('Generate MO After Payment')
    # enable_rounding = fields.Boolean("Rounding Total")
    # rounding_options = fields.Selection([("digits", 'Digits'), ('points', 'Points'), ], string='Rounding Options',
    #                                     default='digits')
    # rounding_journal_id = fields.Many2one('pos.payment.method', "Rounding Payment Method")
    # auto_rounding = fields.Boolean("Auto Rounding")
    enable_bag_charges = fields.Boolean("Bag Charges")
    enable_delivery_charges = fields.Boolean("Delivery Charges")
    delivery_product_id = fields.Many2one('product.product', 'Delivery Product')
    delivery_amount = fields.Float("Delivery Amount")
    enable_manual_lock = fields.Boolean(string="Manual")
    enable_automatic_lock = fields.Boolean(string="Automatic")
    # time_interval = fields.Integer(string="Time Interval (Minutes)", default=5)
    time_interval = fields.Float(string="No.of Copy Receipt", default=5.00)
    enable_keyboard_shortcut = fields.Boolean("Keyboard Shortcut")
    is_scan_product = fields.Boolean(string="Is Scan Product")
    product_sync = fields.Boolean("Product Synchronization")
    display_warehouse_qty = fields.Boolean("Display Warehouse Quantity")
    #     change_stock_locations = fields.Boolean("Change Stock Locations")
    pos_graph = fields.Boolean("POS Graph")
    current_session_report = fields.Boolean("Current Session Report")
    x_report = fields.Boolean("X-Report")
    enable_pos_loyalty = fields.Boolean("Loyalty")
    loyalty_journal_id = fields.Many2one("pos.payment.method", "Loyalty Journal")
    today_sale_report = fields.Boolean("Today Sale Report")
    money_in_out = fields.Boolean("Money In/Out")
    money_in_out_receipt = fields.Boolean("Money In/Out Receipt")
    enable_gift_card = fields.Boolean('Gift Card')
    gift_card_account_id = fields.Many2one('account.account', string="Gift Card Account")
    gift_card_product_id = fields.Many2one('product.product', string="Gift Card Product")
    enable_journal_id = fields.Many2one('pos.payment.method', string="Enable Journal")
    manual_card_number = fields.Boolean('Manual Card No.')
    default_exp_date = fields.Integer('Default Card Expire Months')
    msg_before_card_pay = fields.Boolean('Confirm Message Before Card Payment')
    open_pricelist_popup = fields.Char('Shortcut Key')
    enable_gift_voucher = fields.Boolean('Gift Voucher')
    gift_voucher_account_id = fields.Many2one("account.account", string="Gift Voucher Account")
    gift_voucher_journal_id = fields.Many2one("pos.payment.method", string="Gift Voucher Journal")
    enable_print_last_receipt = fields.Boolean("Print Last Receipt")
    pos_promotion = fields.Boolean("Promotion")
    show_qty = fields.Boolean(string='Display Stock')
    restrict_order = fields.Boolean(string='Restrict Order When Out Of Stock')
    prod_qty_limit = fields.Integer(string="Restrict When Product Qty Remains")
    custom_msg = fields.Char(string="Custom Message")
    enable_print_valid_days = fields.Boolean("Print Product Return Valid days")
    #     default_return_valid_days = fields.Integer("Default Return Valid Days")
    enable_card_charges = fields.Boolean("Card Charges")
    payment_product_id = fields.Many2one('product.product', "Payment Charge Product")
    #     Wallet Functionality
    enable_wallet = fields.Boolean('Wallet')
    wallet_payment_method_id = fields.Many2one("pos.payment.method", "Wallet Payment Method")
    wallet_product = fields.Many2one('product.product', string="Wallet Product")
    wallet_account_id = fields.Many2one('account.account', string="Wallet Account")
    # Order Reservation
    enable_order_reservation = fields.Boolean('Order Reservation')
    reserve_stock_location_id = fields.Many2one('stock.location', 'Reserve Stock Location')
    cancellation_charges_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')],
                                                 'Cancellation Charges Type')
    cancellation_charges = fields.Float('Cancellation Charges')
    cancellation_charges_product_id = fields.Many2one('product.product', 'Cancellation Charges Product')
    prod_for_payment = fields.Many2one('product.product', string='Paid Amount Product',
                                       help="This is a dummy product used when a customer pays partially. This is a workaround to the fact that Odoo needs to have at least one product on the order to validate the transaction.")
    refund_amount_product_id = fields.Many2one('product.product', 'Refund Amount Product')
    enable_pos_welcome_mail = fields.Boolean("Send Welcome Mail")
    allow_reservation_with_no_amount = fields.Boolean("Allow Reservation With 0 Amount")
    # Discard Product
    discard_product = fields.Boolean(string="Discard Product")
    discard_location = fields.Many2one('stock.location', string="Discard Location")
    picking_type = fields.Many2one('stock.picking.type', string="Picking Type")
    # Payment_summary_report
    payment_summary = fields.Boolean(string="Payment Summary")
    current_month_date = fields.Boolean(string="Current Month Date")
    # User Operation Restrict
    enable_operation_restrict = fields.Boolean("Operations Restrict")
    pos_managers_ids = fields.Many2many('res.users', 'posconfig_partner_rel', 'location_id', 'partner_id',
                                        string='Authorised Managers')
    # Product Summary Report
    print_product_summary = fields.Boolean(string="Product Summary Report")
    no_of_copy_receipt = fields.Integer(string="No.of Copy Receipt", default=1)
    product_summary_month_date = fields.Boolean(string="Display Current Month Date")
    signature = fields.Boolean(string="Signature")
    # Order Summary Report
    enable_order_summary = fields.Boolean(string='Order Summary Report')
    order_summary_no_of_copies = fields.Integer(string="No. of Copy Receipt", default=1)
    order_summary_current_month = fields.Boolean(string="Current month")
    order_summary_signature = fields.Boolean(string="Order Signature")
    # Print Audit Report
    print_audit_report = fields.Boolean("Print Audit Report")
    # POS Serial/lots
    enable_pos_serial = fields.Boolean("Enable POS serials")
    restrict_lot_serial = fields.Boolean("Restrict Lot/Serial Quantity")
    product_exp_days = fields.Integer("Product Expiry Days", default="0")
    # POS Multi-Store
    enable_multi_store = fields.Boolean(string='Multi Store')
    header_info = fields.Selection([('company', 'Company'), ('store', 'Store')], string="Select Receipt Header",
                                   required=True,
                                   default="company")
    # Customer Display
    customer_display = fields.Boolean("Customer Display")
    enable_customer_rating = fields.Boolean("Customer Display Rating")
    image_interval = fields.Integer("Image Interval", default=10)
    customer_display_details_ids = fields.One2many('customer.display', 'config_id', "Customer Display Details")
    set_customer = fields.Boolean("Select/Create Customer")
    product_expiry_report = fields.Boolean(string="Product Expiry Dashboard")
    # Out of Stock
    out_of_stock_detail = fields.Boolean(string="Out of Stock Detail")
    enable_int_trans_stock = fields.Boolean(string="Internal Stock Transfer")
    # Order sync
    orders_sync = fields.Boolean("Order Sync")
    # Vertical Categories
    vertical_categories = fields.Boolean(string="Vertical Categories")
    auto_close = fields.Boolean(string="Auto Close")
    # Sale Order Extension
    pos_sale_order = fields.Boolean("Sale Orders")
    sale_order_operations = fields.Selection([('draft', 'Quotations'),
                                              ('confirm', 'Confirm'), ('paid', 'Paid')], "Sale order operation",
                                             default="draft")
    sale_order_last_days = fields.Char("Load Orders to Last days")
    # sale_order_record_per_page = fields.Char("Record Per Page")
    paid_amount_product = fields.Many2one('product.product', string='Order Paid Amount Product',
                                          domain=[('available_in_pos', '=', True)])
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    sale_order_invoice = fields.Boolean("Invoice")

    enable_debit = fields.Boolean(string="Sales Debit")
    enable_credit = fields.Boolean('Credit Management')
    receipt_balance = fields.Boolean('Display Balance info in Receipt')
    print_ledger = fields.Boolean('Credit Statement')
    pos_crdt_journal_id = fields.Many2one('pos.payment.method', string='Select Journal')
    prod_for_credit_payment = fields.Many2one('product.product', string='Credit Paid Amount Product',
                                              help="This is a dummy product used when a customer pays credit. This is a workaround to the fact that Odoo needs to have at least one product on the order to validate the transaction.")
    # Default Customer
    default_partner_id = fields.Many2one('res.partner', string="Default Customer")
    # Remove Product Image
    product_pictures = fields.Boolean('Product Pictures', default=True)
    enable_change_pin = fields.Boolean(string="Change User Pin")
    z_report = fields.Boolean(string="Z Report")
    change_product_uom = fields.Boolean(string="Change Product UOM")
    enable_customer_purchase_history = fields.Boolean(string='Customer Purchase History')
    send_order_kitchen = fields.Boolean("Send to kitchen")
    enable_combo = fields.Boolean('Enable Combo')
    edit_combo = fields.Boolean('Single Click for Edit Combo')
    hide_uom = fields.Boolean('Hide UOM')


class pos_order(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_table_draft_orders(self, table_id):

        table_orders = self.search_read(
            domain=[('state', '=', 'draft'), ('table_id', '=', table_id)],
            fields=self._get_fields_for_draft_order())

        self._get_order_lines(table_orders)
        self._get_payment_lines(table_orders)

        for order in table_orders:
            order['pos_session_id'] = order['session_id'][0]
            # order['uid'] = search(r"\d{5,}-\d{3,}-\d{4,}", order['pos_reference']).group(0)
            order['uid'] = order['pos_reference']
            order['name'] = order['pos_reference']
            order['creation_date'] = order['create_date']
            order['server_id'] = order['id']
            if order['fiscal_position_id']:
                order['fiscal_position_id'] = order['fiscal_position_id'][0]
            if order['pricelist_id']:
                order['pricelist_id'] = order['pricelist_id'][0]
            if order['partner_id']:
                order['partner_id'] = order['partner_id'][0]
            if order['table_id']:
                order['table_id'] = order['table_id'][0]

            if not 'lines' in order:
                order['lines'] = []
            if not 'statement_ids' in order:
                order['statement_ids'] = []

            del order['id']
            del order['session_id']
            del order['pos_reference']
            del order['create_date']

        return table_orders

    # @api.model
    # def broadcast_order_data(self, new_order):
    #     notifications = []
    #     vals = {}
    #     pos_order = self.search([('lines.state', 'not in', ['cancel', 'done']),
    #                              ('amount_total', '>', 0.00)])
    #     manager_id = self.env['res.users'].search([('kitchen_screen_user', '=', 'manager')], limit=1)
    #     screen_table_data = []
    #     for order in pos_order:
    #         order_line_list = []
    #         for line in order.lines:
    #             order_line = {
    #                 'id': line.id,
    #                 'name': line.product_id.display_name,
    #                 'qty': line.qty,
    #                 'table': line.order_id.table_id.name,
    #                 'floor': line.order_id.table_id.floor_id.name,
    #                 'time': self.get_session_date(line),
    #                 'state': line.state,
    #                 'note': line.order_line_note,
    #                 'categ_id': line.product_id.product_tmpl_id.pos_categ_id.id,
    #                 'order': line.order_id.id,
    #                 'pos_cid': line.pos_cid,
    #                 'user': line.create_uid.id,
    #                 'route_id': line.product_id.product_tmpl_id.route_ids.active,
    #             }
    #             order_line_list.append(order_line)
    #         order_dict = {
    #             'order_id': order.id,
    #             'order_name': order.name,
    #             'order_time': self.get_order_date(order),
    #             'table': order.table_id.name,
    #             'floor': order.table_id.floor_id.name,
    #             'customer': order.partner_id.name,
    #             'order_lines': order_line_list,
    #             'total': order.amount_total,
    #             'note': order.note,
    #             'user_id': order.user_id.id,
    #         }
    #         screen_table_data.append(order_dict)
    #     kitchen_group_data = {}

    #     sort_group = sorted(screen_table_data, key=itemgetter('user_id'))
    #     for key, value in itertools.groupby(sort_group, key=itemgetter('user_id')):
    #         if key not in kitchen_group_data:
    #             kitchen_group_data.update({key: [x for x in value]})
    #         else:
    #             kitchen_group_data[key] = [x for x in value]
    #     if kitchen_group_data:
    #         for user_id in kitchen_group_data:
    #             user = self.env['res.users'].browse(user_id)
    #             if user and user.cook_user_ids:
    #                 for cook_user_id in user.cook_user_ids:
    #                     if len(vals) > 0:
    #                         d1 = kitchen_group_data[user_id]
    #                         for each_order in d1:
    #                             vals['orders'].append(each_order)
    #                     else:
    #                         vals = {
    #                             "orders": kitchen_group_data[user_id],
    #                         }
    #                     if new_order:
    #                         vals['new_order'] = new_order
    #                     notifications.append(
    #                         ((self._cr.dbname, 'pos.order.line', cook_user_id.id), {'screen_display_data': vals}))
    #             if user and user.kitchen_screen_user != 'cook':
    #                 notifications.append(
    #                     ((self._cr.dbname, 'pos.order.line', manager_id.id), {'screen_display_data': vals}))
    #     else:
    #         notifications.append(
    #             ((self._cr.dbname, 'pos.order.line', manager_id.id), {'screen_display_data': vals}))
    #         cook_user_ids = self.env['res.users'].search([('kitchen_screen_user', '=', 'cook')])
    #         if cook_user_ids:
    #             for each_cook_id in cook_user_ids:
    #                 notifications.append(
    #                     ((self._cr.dbname, 'pos.order.line', each_cook_id.id), {'screen_display_data': vals}))
    #     if notifications:
    #         self.env['bus.bus'].sendmany(notifications)
    #     return True

    @api.model
    def broadcast_order_data(self, new_order):
        notifications = []
        vals = {}
        pos_order = self.search([('lines.state', 'not in', ['cancel', 'done']),
                                 ('amount_total', '>', 0.00)])
        manager_id = self.env['res.users'].search([('pos_user_type', '=', 'cashier')], limit=1)
        screen_table_data = []
        for order in pos_order:
            order_line_list = []
            est_ordertime = 0
            for line in order.lines:
                bom_list = []
                combo_data = False
                est_ordertime += line.product_id.make_time
                if line.bom_lines:
                    bom_line_ids = self.env['pos.orderline.bom.line'].search([('pos_order_line_id', '=', line.id)])
                    for bom_line_in_orderline in bom_line_ids:
                        bom_list.append({
                            'product_id': bom_line_in_orderline.product_id.id,
                            'qty': bom_line_in_orderline.qty,
                        })
                est_ordertime += line.product_id.make_time
                combo_data = False
                if line.is_main_combo_product:
                    combo_data = ast.literal_eval(line.tech_combo_data) if line and line.tech_combo_data else False
                order_line = {
                    'id': line.id,
                    'name': line.product_id.display_name,
                    'qty': line.qty,
                    # 'table': line.order_id.table_id.name,
                    # 'floor': line.order_id.table_id.floor_id.name,
                    # 'time': self.get_session_date(line),
                    'state': line.state,
                    'note': line.line_note,
                    'categ_id': line.product_id.product_tmpl_id.pos_categ_id.id,
                    'order': line.order_id.id,
                    # 'pos_cid': line.pos_cid,
                    'user': line.create_uid.id,
                    'priority': line.priority,
                    'combo_data': combo_data,
                    'bom_list': bom_list,
                    # 'route_id': line.product_id.product_tmpl_id.route_ids.active,
                }
                order_line_list.append(order_line)
            date_order = str(order.date_order)
            tables = ''
            if order and order.table_ids:
                restaurant_tables = self.env['restaurant.table'].search_read([('id', 'in', order.table_ids.ids)],
                                                                             ['name'])
                if restaurant_tables:
                    for table in restaurant_tables:
                        tables += table.get('name') + ', '
            order_dict = {
                'order_id': order.id,
                'order_name': order.name,
                'est_ordertime': est_ordertime,
                # 'order_time': self.get_order_date(order),
                # 'table': order.table_id.name,
                # 'floor': order.table_id.floor_id.name,
                'customer': order.partner_id.name,
                'order_lines': order_line_list,
                'total': order.amount_total,
                'note': order.note,
                'user_id': order.user_id.id,
                'table': tables[:-2] if tables else '',
            }
            settings_kitchen_screen_timer = self.env['ir.config_parameter'].sudo().search(
                [('key', '=', 'kitchen_screen_timer')])
            if settings_kitchen_screen_timer and settings_kitchen_screen_timer.value:
                order_dict['est_ordertime'] = est_ordertime
                order_dict['stop_timer'] = False
            else:
                order_dict['est_ordertime'] = 0
                order_dict['stop_timer'] = True
            screen_table_data.append(order_dict)
        kitchen_group_data = {}

        sort_group = sorted(screen_table_data, key=itemgetter('user_id'))
        for key, value in itertools.groupby(sort_group, key=itemgetter('user_id')):
            if key not in kitchen_group_data:
                kitchen_group_data.update({key: [x for x in value]})
            else:
                kitchen_group_data[key] = [x for x in value]
        if kitchen_group_data:
            for user_id in kitchen_group_data:
                user = self.env['res.users'].browse(user_id)
                if user and user.cook_user_ids:
                    for cook_user_id in user.cook_user_ids:
                        if len(vals) > 0:
                            d1 = kitchen_group_data[user_id]
                            for each_order in d1:
                                vals['orders'].append(each_order)
                        else:
                            vals = {
                                "orders": kitchen_group_data[user_id],
                            }
                        if new_order:
                            vals['new_order'] = new_order
                        notifications.append(
                            ((self._cr.dbname, 'pos.order.line', cook_user_id.id), {'screen_display_data': vals}))
                if user and user.pos_user_type != 'cook':
                    notifications.append(
                        ((self._cr.dbname, 'pos.order.line', manager_id.id), {'screen_display_data': vals}))
        else:
            notifications.append(
                ((self._cr.dbname, 'pos.order.line', manager_id.id), {'screen_display_data': vals}))
            cook_user_ids = self.env['res.users'].search([('pos_user_type', '=', 'cook')])
            if cook_user_ids:
                for each_cook_id in cook_user_ids:
                    notifications.append(
                        ((self._cr.dbname, 'pos.order.line', each_cook_id.id), {'screen_display_data': vals}))
        if notifications:
            self.env['bus.bus'].sendmany(notifications)
        return True

    #     @api.model
    #     def broadcast_order_data(self, new_order):
    #         print("\n\n\nbroadcast_order---->",new_order)
    #         notifications = []
    #         vals = {}
    #         SQL = """
    #                 select DISTINCT order_id from pos_order_line where state not in ('cancel','done')
    #                 and create_date >='%s' and company_id = %s
    #          """%(str(date.today()) + ' 00:00:00', self.env.user.company_id.id)
    #         self._cr.execute(SQL)
    #         pos_order = self._cr.dictfetchall()
    # #         pos_order = self.search([('lines.state', 'not in', ['cancel', 'done']),('create_date','>=', str(date.today()) + ' 00:00:00')])
    #         pos_order_id_list = []
    #         pos_orders = []
    #         if pos_order:
    #             for order in pos_order:
    #                 pos_order_id_list.append(order.get('order_id'))
    #             pos_orders = self.browse(pos_order_id_list)
    #         screen_table_data = []
    #         for order in pos_orders:
    #             order_line_list = []
    #             est_ordertime = 0
    #             for line in order.lines:
    #                 bom_list = []
    #                 combo_data = False
    #                 est_ordertime += line.product_id.make_time

    #                 if line.bom_lines:
    #                     bom_line_ids = self.env['pos.orderline.bom.line'].search([('pos_order_line_id','=',line.id)])
    #                     for bom_line_in_orderline in bom_line_ids:
    #                         bom_list.append({
    #                             'product_id':bom_line_in_orderline.product_id.id,
    #                             'qty':bom_line_in_orderline.qty,
    #                         })
    # #                 if line.product_id.send_to_kitchen and not line.is_combo_line:
    # #                     modifier_list = []
    # #                     if line and not line.modifier:
    # #                             modifier_line_ids = self.env['modifier.order.line'].search([('line_id','=',line.id)])
    # #                             for modifier_line_id in modifier_line_ids:
    # #                                 modifier_list.append({
    # #                                     'name':modifier_line_id.name,
    # #                                     'qty': modifier_line_id.qty
    # #                                 })
    # #                     if line.is_main_combo_product:
    # #                         combo_data = ast.literal_eval(line.tech_combo_data) if line and line.tech_combo_data else False
    # #                     order_line = {
    # #                         'id': line.id,
    # #                         'name': line.product_id.display_name,
    # #                         'qty': line.qty,
    # #                         'table': line.order_id.table_id.name,
    # #                         'floor': line.order_id.table_id.floor_id.name,
    # #     #                     'time': self.get_timezone_date(line),
    # #                         'time': self.get_time(line.create_date),
    # #                         'state': line.state,
    # #                         'note': line.line_note,
    # #                         'categ_id': line.product_id.product_tmpl_id.pos_categ_id.id,
    # #                         'order': line.order_id.id,
    # #                         'pos_cid': line.pos_cid,
    # #                         'user': line.create_uid.id,
    # # #                         'route_id': line.product_id.product_tmpl_id.route_ids.active,
    # #                         'route_id':False,
    # #                         'modifier_list':modifier_list,
    # #                         'bom_list': bom_list,
    # #                         'modifier':line.modifier,
    # #                         'is_takeaway':line.is_takeaway,
    # #                         'is_deliver': line.deliver,
    # #                         'priority':line.priority,
    # #                         'combo_data':combo_data,
    # #                     }
    # #                     order_line_list.append(order_line)
    #             date_order = str(order.date_order)
    #             tables = ''
    #             # if order and order.table_ids:
    #             #     restaurant_tables = self.env['restaurant.table'].search_read([('id','in',order.table_ids.ids)], ['name'])
    #             #     if restaurant_tables:
    #             #         for table in restaurant_tables:
    #             #             tables += table.get('name') + ', '
    #             order_dict = {
    #                 'order_id': order.id,
    #                 'order_name': order.name,
    # #                 'order_time': date_order.split(" ")[1],
    #                 # 'order_bank_statement_linese': self.get_time(order.create_date),
    #                 'table': tables[:-2] if tables else '',
    #                 # 'floor': order.table_id.floor_id.name,
    #                 'customer': order.partner_id.name,
    #                 'order_lines': order_line_list,
    #                 'total': order.amount_total,
    #                 'note': order.note,
    #                 'increment_number':order.increment_number if int(order.increment_number) > 0 else 0,
    #                 'est_ordertime':est_ordertime,
    #                 'user_id':order.user_id.id,
    #             }
    #             settings_kitchen_screen_timer = self.env['ir.config_parameter'].sudo().search([('key', '=', 'kitchen_screen_timer')])
    #             if settings_kitchen_screen_timer and settings_kitchen_screen_timer.value:
    #                 order_dict['est_ordertime'] = est_ordertime
    #                 order_dict['stop_timer'] = False
    #             else:
    #                 order_dict['est_ordertime'] = 0
    #                 order_dict['stop_timer'] = True
    #             screen_table_data.append(order_dict)
    #         kitchen_group_data = {}
    #         sort_group = sorted(screen_table_data, key=itemgetter('user_id'))
    #         for key, value in itertools.groupby(sort_group, key=itemgetter('user_id')):
    #             if key not in kitchen_group_data:
    #                 kitchen_group_data.update({key:[x for x in value]})
    #             else:
    #                 kitchen_group_data[key] = [x for x in value]
    #         for user_id in kitchen_group_data:
    #             user = self.env['res.users'].browse(user_id)

    #             print("\n\n\nuser---->",user)
    #             if user and user.cook_user_ids:
    #                 for cook_user_id in user.cook_user_ids:
    #                     if 'orders' not in vals:
    #                         vals['orders'] = []
    #                     for itm in kitchen_group_data[user_id]:
    #                         if itm not in vals['orders']:
    #                             vals['orders'].append(itm)
    #                     if new_order:
    #                         vals['new_order'] = new_order
    #                     print("\n\n\n\n------->")
    #                     notifications.append(((self._cr.dbname, 'pos.order.line', cook_user_id.id), {'screen_display_data': vals}))
    #             # if user and user.user_role == 'cook_manager':
    #             #     vals = {
    #             #         "orders": kitchen_group_data[user_id],
    #             #     }
    #             #     notifications.append(((self._cr.dbname, 'pos.order.line', user.id), {'screen_display_data': vals}))
    #         if notifications:
    #             print("\n\n\nnotifications---->",notifications)
    #             self.env['bus.bus'].sendmany(notifications)
    #         return True
    @api.model
    def load_order_details(self, order_id):
        order_obj = self.browse(int(order_id))
        lines = []
        if order_obj:
            for each in order_obj.lines:
                line = self.load_order_line_details(each.id)
                if line:
                    lines.append(line[0])
        return lines

    @api.model
    def load_order_line_details(self, line_id):
        data = {}
        line_obj = self.env['pos.order.line'].search_read([('id', '=', line_id)])
        if line_obj:
            order_obj = self.browse(line_obj[0].get('order_id')[0])
            data['id'] = line_obj[0].get('id')
            data['product_id'] = line_obj[0].get('product_id')
            data['uom_id'] = self.env['product.product'].browse(line_obj[0].get('product_id')[0]).uom_id.name
            data['company_id'] = line_obj[0].get('company_id')
            data['qty'] = line_obj[0].get('qty')
            data['order_line_note'] = line_obj[0].get('order_line_note')
            data['order_id'] = line_obj[0].get('order_id')
            data['state'] = line_obj[0].get('state')
            data['pos_reference'] = order_obj.pos_reference
            data['table_id'] = [order_obj.table_id.id, order_obj.table_id.name] if order_obj.table_id else False
            data[
                'floor_id'] = order_obj.table_id.floor_id.name if order_obj.table_id and order_obj.table_id.floor_id else False
        return [data]

    @api.model
    def get_customer_product_history(self, product_id, partner_id):
        sql = """
                SELECT pol.product_id,to_char(po.date_order, 'DD-MM-YYYY') AS date_order,pol.price_subtotal_incl AS total, pol.qty from pos_order AS po
                LEFT JOIN pos_order_line AS pol ON pol.order_id = po.id 
                WHERE pol.product_id = %s AND po.partner_id = %s
                ORDER BY po.date_order Desc LIMIT 1
                """ % (product_id, partner_id)
        self.env.cr.execute(sql)
        res_all = self.env.cr.dictfetchall()
        return res_all

    @api.model
    def get_all_product_history(self, product_ids, partner_id):
        sql = """
                SELECT po.partner_id, pol.product_id,pol.qty, pol.price_subtotal_incl, to_char(po.date_order, 'DD-MM-YYYY') AS date_order FROM pos_order_line AS pol
                INNER JOIN pos_order AS po ON po.id = pol.order_id 
                WHERE po.date_order = ( SELECT MAX (date_order) FROM pos_order WHERE partner_id IN ('%s')) 
                """ % (partner_id)
        self.env.cr.execute(sql)
        res_all_last_purchase_history = self.env.cr.dictfetchall()
        if len(res_all_last_purchase_history) != 0:
            res_single_date_purchase_history = res_all_last_purchase_history[0].get('date_order')
            sql = """
                    SELECT DISTINCT ON (pol.product_id) pol.product_id, to_char(po.date_order, 'DD-MM-YYYY') AS date_order, pol.qty, Round(pol.price_subtotal_incl,2) AS price_subtotal_incl 
                    FROM pos_order_line AS pol
                    INNER JOIN pos_order AS po on po.id = pol.order_id
                    WHERE pol.product_id IN (%s) AND po.partner_id = %s
                    ORDER BY pol.product_id, po.date_order DESC
                    """ % (','.join(map(str, product_ids)), partner_id)
            self.env.cr.execute(sql)
            res_all_product_history = self.env.cr.dictfetchall()
            res_all = {'res_product_history': res_all_product_history,
                       'res_last_purchase_history': res_all_last_purchase_history,
                       'date_order': res_single_date_purchase_history}
            return res_all
        else:
            return False

    def check_order_delivery_type(self):
        if self.delivery_type == 'pending' and self.state == 'draft':
            action_id = self.env.ref('point_of_sale.action_pos_payment')
            return {
                'name': _(action_id.name),
                'type': action_id.type,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': action_id.res_model,
                'target': 'new',
                'context': {'from_delivery': True},
            }

        elif self.delivery_type == 'pending' and self.state == 'paid':
            self.write({'delivery_type': 'delivered'})
            return {'type': 'ir.actions.client', 'tag': 'reload'}

    # @api.multi
    # def check_order_delivery_type(self):
    #     if self.delivery_type == 'pending' and self.state == 'draft':
    #         action_id = self.env.ref('flexibite_com_advance.action_pos_payment_flexibite')
    #         return {
    #             'name': action_id.name,
    #             'type': action_id.type,
    #             'res_model': action_id.res_model,
    #             'view_type': action_id.view_type,
    #             'view_id': action_id.view_id.id,
    #             'view_mode': action_id.view_mode,
    #             "context": {"from_delivery": True},
    #             'target': 'new',
    #         }
    #
    #     elif self.delivery_type == 'pending' and self.state == 'paid' or self.state == 'done' or self.state == 'invoiced':
    #         self.write({'delivery_type': 'delivered'})
    #         return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def change_delivery_state(self, order_id, state):
        order = self.browse(order_id)
        if order:
            order.update({'delivery_type': state})
            return order.read()[0]

    @api.model
    def make_delivery_payment(self, order_id, journal_id):
        order = self.browse(order_id)
        if order:
            order.update({'delivery_type': 'delivered'})
            values = self.env['pos.make.payment'].with_context({
                'active_id': order.id,
                'default_journal_id': journal_id,
                'default_amount': order.amount_total
            }).default_get(['journal_id', 'amount'])
            self.env['pos.make.payment'].with_context({'active_id': order.id, 'ctx_is_postpaid': True}).create(
                values).check()
            return order.read()[0]

    @api.model
    def load_ir_config_parameter(self):
        record = {}
        settings_is_rfid_login = self.env['ir.config_parameter'].sudo().search([('key', '=', 'is_rfid_login')])
        settings_pos_theme = self.env['ir.config_parameter'].sudo().search([('key', '=', 'theme_selector')])
        if settings_is_rfid_login:
            record['is_rfid_login'] = settings_is_rfid_login.value
        if settings_pos_theme:
            record['pos_theme'] = settings_pos_theme.value
        return [record]

    @api.model
    def get_dashboard_data(self):
        company_id = self.env['res.users'].browse([self._uid]).company_id.id
        res_pos_order = {'total_sales': 0, 'total_orders': 0}
        active_sessions = self.env['pos.session'].search([('state', '=', 'opened')]).ids
        closed_sessions = self.env['pos.session'].search(
            [('stop_at', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00"),
             ('stop_at', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59"),
             ('state', 'in', ['closing_control', 'closed'])]).ids
        res_pos_order['closed_sessions'] = len(closed_sessions)
        res_pos_order['active_sessions'] = len(active_sessions)
        pos_ids = self.search([('company_id', '=', company_id),
                               ('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00"),
                               ('date_order', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59"), ])
        if pos_ids:
            total_sales = 0;
            existing_partner_sale = 0
            new_partner_sale = 0
            without_partner_sale = 0
            for pos_id in pos_ids:
                total_sales += pos_id.amount_total
                if pos_id.partner_id:
                    orders = self.search([('partner_id', '=', pos_id.partner_id.id),
                                          ('company_id', '=', company_id),
                                          ('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00"),
                                          ('date_order', '<=',
                                           fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59"), ])
                    if orders and len(orders) > 1:
                        existing_partner_sale += pos_id.amount_total
                    else:
                        new_partner_sale += pos_id.amount_total
                else:
                    orders = self.search([('partner_id', '=', False),
                                          ('company_id', '=', company_id),
                                          ('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00"),
                                          ('date_order', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59")])

                    if orders and len(orders) > 1:
                        without_partner_sale += pos_id.amount_total
            res_pos_order['client_based_sale'] = {'new_client_sale': new_partner_sale,
                                                  'existing_client_sale': existing_partner_sale,
                                                  'without_client_sale': without_partner_sale}
            res_pos_order['total_sales'] = total_sales
            res_pos_order['total_orders'] = len(pos_ids)
            current_time_zone = self.env.user.tz or 'UTC'
            #             orders = []
            if self.env.user.tz:
                tz = pytz.timezone(self.env.user.tz)
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            sdate = c_time.strftime("%Y-%m-%d 00:00:00")
            edate = c_time.strftime("%Y-%m-%d 23:59:59")
            if sign == '-':
                start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                        minutes=min_tz)).strftime(
                    "%Y-%m-%d %H:%M:%S")
                end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                      minutes=min_tz)).strftime(
                    "%Y-%m-%d %H:%M:%S")
            if sign == '+':
                start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                        minutes=min_tz)).strftime(
                    "%Y-%m-%d %H:%M:%S")
                end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                      minutes=min_tz)).strftime(
                    "%Y-%m-%d %H:%M:%S")
            self._cr.execute("""SELECT extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_hour,
                                       SUM((pol.qty * pol.price_unit) * (100 - pol.discount) / 100) AS price_total
                            FROM pos_order_line AS pol
                            LEFT JOIN pos_order po ON (po.id=pol.order_id)
                            WHERE po.date_order >= '%s'
                              AND po.date_order <= '%s'
                            GROUP BY  extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s');
                            """ % (current_time_zone, start_date, end_date, current_time_zone))
            result_data_hour = self._cr.dictfetchall()
            hour_lst = [hrs for hrs in range(0, 24)]
            for each in result_data_hour:
                if each['date_order_hour'] != 23:
                    each['date_order_hour'] = [each['date_order_hour'], each['date_order_hour'] + 1]
                else:
                    each['date_order_hour'] = [each['date_order_hour'], 0]
                hour_lst.remove(int(each['date_order_hour'][0]))
            for hrs in hour_lst:
                hr = []
                if hrs != 23:
                    hr += [hrs, hrs + 1]
                else:
                    hr += [hrs, 0]
                result_data_hour.append({'date_order_hour': hr, 'price_total': 0.0})
            sorted_hour_data = sorted(result_data_hour, key=lambda l: l['date_order_hour'][0])
            res_pos_order['sales_based_on_hours'] = sorted_hour_data
            # this month data
        res_curr_month = self.pos_order_month_based(1)
        res_pos_order['current_month'] = res_curr_month
        #             Last 6 month data
        last_6_month_res = self.pos_order_month_based(12)
        res_pos_order['last_6_month_res'] = last_6_month_res
        return res_pos_order

    def pos_order_month_based(self, month_count):
        tz = pytz.utc
        c_time = datetime.now(tz)
        hour_tz = int(str(c_time)[-5:][:2])
        min_tz = int(str(c_time)[-5:][3:])
        sign = str(c_time)[-6][:1]
        current_time_zone = self.env.user.tz or 'UTC'
        stdate = c_time.strftime("%Y-%m-01 00:00:00")
        eddate = (c_time + relativedelta(day=1, months=+month_count, days=-1)).strftime("%Y-%m-%d 23:59:59")
        # this month data 
        if sign == '-':
            mon_stdate = (datetime.strptime(stdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                     minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            mon_eddate = (datetime.strptime(eddate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                     minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
        if sign == '+':
            mon_stdate = (datetime.strptime(stdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                     minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            mon_eddate = (datetime.strptime(eddate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                     minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
        if month_count == 12:
            self._cr.execute("""SELECT extract(month from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_month,
                                   SUM((pol.qty * pol.price_unit) * (100 - pol.discount) / 100) AS price_total
                        FROM pos_order_line AS pol
                        LEFT JOIN pos_order po ON (po.id=pol.order_id)
                        WHERE po.date_order >= '%s'
                          AND po.date_order <= '%s'
                        GROUP BY extract(month from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s');
                        """ % (current_time_zone, mon_stdate, mon_eddate, current_time_zone))
        else:
            self._cr.execute("""SELECT extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_day,
                                        extract(month from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_month,
                                       SUM((pol.qty * pol.price_unit) * (100 - pol.discount) / 100) AS price_total
                            FROM pos_order_line AS pol
                            LEFT JOIN pos_order po ON (po.id=pol.order_id)
                            WHERE po.date_order >= '%s'
                              AND po.date_order <= '%s'
                            GROUP BY  extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s'),
                                extract(month from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s')
                                ORDER BY extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') DESC;
                            """ % (
                current_time_zone, current_time_zone, mon_stdate, mon_eddate, current_time_zone, current_time_zone,
                current_time_zone))
        result_this_month = self._cr.dictfetchall()
        return result_this_month

    @api.model
    def graph_date_on_canvas(self, start_date, end_date):
        data = {}
        company_id = self.env['res.users'].browse([self._uid]).company_id.id
        domain = [('company_id', '=', company_id)]
        if start_date:
            domain += [('date_order', '>=', start_date)]
        else:
            domain += [('date_order', '>=', str(fields.Date.today()) + " 00:00:00")]
        if end_date:
            domain += [('date_order', '<=', end_date)]
        else:
            domain += [('date_order', '<=', str(fields.Date.today()) + " 23:59:59")]
        pos_ids = self.search(domain)
        if pos_ids:
            self._cr.execute("""select aj.name, aj.id, sum(amount)
                                from account_bank_statement_line as absl,
                                     account_bank_statement as abs,
                                     account_journal as aj 
                                where absl.statement_id = abs.id
                                      and abs.journal_id = aj.id 
                                     and absl.pos_statement_id IN %s
                                group by aj.name, aj.id """ % "(%s)" % ','.join(map(str, pos_ids.ids)))
            data = self._cr.dictfetchall()
        total = 0.0
        for each in data:
            total += each['sum']
        for each in data:
            each['per'] = (each['sum'] * 100) / total
        return data

    @api.model
    def session_details_on_canvas(self):
        data = {}
        domain_active_session = []
        close_session_list = []
        active_session_list = []
        company_id = self.env['res.users'].browse([self._uid]).company_id.id
        domain = [('company_id', '=', company_id),
                  ('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00"),
                  ('date_order', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59")]
        domain_active_session += domain
        domain_active_session += [('state', '=', 'paid')]
        domain += [('state', '=', 'done')]
        active_pos_ids = self.search(domain_active_session)
        posted_pos_ids = self.search(domain)
        if active_pos_ids:
            self._cr.execute("""select aj.name, aj.id, sum(amount),abs.pos_session_id
                                from account_bank_statement_line as absl,
                                     account_bank_statement as abs,
                                     account_journal as aj 
                                where absl.statement_id = abs.id
                                      and abs.journal_id = aj.id 
                                     and absl.pos_statement_id IN %s
                                group by aj.name, abs.pos_session_id, aj.id """ % "(%s)" % ','.join(
                map(str, active_pos_ids.ids)))
            active_session_data = self._cr.dictfetchall()
            session_group = {}
            sort_group = sorted(active_session_data, key=itemgetter('pos_session_id'))
            for key, value in itertools.groupby(sort_group, key=itemgetter('pos_session_id')):
                if key not in session_group:
                    session_group.update({key: [x for x in value]})
                else:
                    session_group[key] = [x for x in value]
            for k, v in session_group.items():
                total_sum = 0
                for each in v:
                    total_sum += float(each['sum'])
                active_session_list.append(
                    {'pos_session_id': self.env['pos.session'].browse(k).read(), 'sum': total_sum})
        if posted_pos_ids:
            self._cr.execute("""select aj.name, aj.id, sum(amount),abs.pos_session_id
                                from account_bank_statement_line as absl,
                                     account_bank_statement as abs,
                                     account_journal as aj 
                                where absl.statement_id = abs.id
                                      and abs.journal_id = aj.id 
                                     and absl.pos_statement_id IN %s
                                group by aj.name, abs.pos_session_id, aj.id """ % "(%s)" % ','.join(
                map(str, posted_pos_ids.ids)))

            posted_session_data = self._cr.dictfetchall()
            session_group = {}
            sort_group = sorted(posted_session_data, key=itemgetter('pos_session_id'))
            for key, value in itertools.groupby(sort_group, key=itemgetter('pos_session_id')):
                if key not in session_group:
                    session_group.update({key: [x for x in value]})
                else:
                    session_group[key] = [x for x in value]
            for k, v in session_group.items():
                total_sum = 0
                for each in v:
                    total_sum += float(each['sum'])
                close_session_list.append(
                    {'pos_session_id': self.env['pos.session'].browse(k).read(), 'sum': total_sum})
        return {'close_session': close_session_list, 'active_session': active_session_list}

    @api.model
    def graph_best_product(self, start_date, end_date):
        data = {}
        company_id = self.env['res.users'].browse([self._uid]).company_id.id
        domain = [('company_id', '=', company_id)]
        if start_date:
            domain += [('date_order', '>=', start_date)]
        else:
            domain += [('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00")]
        if end_date:
            domain += [('date_order', '<=', end_date)]
        else:
            domain += [('date_order', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59")]
        pos_ids = self.search(domain)
        if pos_ids:
            order_ids = []
            for pos_id in pos_ids:
                order_ids.append(pos_id.id)
            self._cr.execute("""
                SELECT pt.name, sum(psl.qty), SUM((psl.qty * psl.price_unit) * (100 - psl.discount) / 100) AS price_total FROM pos_order_line AS psl
                JOIN pos_order AS po ON (po.id = psl.order_id)
                JOIN product_product AS pp ON (psl.product_id = pp.id)
                JOIN product_template AS pt ON (pt.id = pp.product_tmpl_id)
                where po.id IN %s
                GROUP BY pt.name
                ORDER BY sum(psl.qty) DESC limit 50;
                """ % "(%s)" % ','.join(map(str, pos_ids.ids)))
            data = self._cr.dictfetchall()
        return data

    @api.model
    def orders_by_salesperson(self, start_date, end_date):
        data = {}
        company_id = self.env['res.users'].browse([self._uid]).company_id.id
        domain = [('company_id', '=', company_id)]
        if start_date:
            domain += [('date_order', '>=', start_date)]
        else:
            domain += [('date_order', '>=', fields.Date.today().strftime('%m/%d/%Y') + " 00:00:00")]
        if end_date:
            domain += [('date_order', '<=', end_date)]
        else:
            domain += [('date_order', '<=', fields.Date.today().strftime('%m/%d/%Y') + " 23:59:59")]
        pos_ids = self.search(domain)
        if pos_ids:
            order_ids = []
            for pos_id in pos_ids:
                order_ids.append(pos_id.id)
            self._cr.execute("""
                SELECT po.user_id, count(DISTINCT(po.id)) As total_orders, SUM((psl.qty * psl.price_unit) * (100 - psl.discount) / 100) AS price_total FROM pos_order_line AS psl
                JOIN pos_order AS po ON (po.id = psl.order_id)
                where po.id IN %s
                GROUP BY po.user_id
                ORDER BY count(DISTINCT(po.id)) DESC;
                """ % "(%s)" % ','.join(map(str, pos_ids.ids)))
            data = self._cr.dictfetchall()
        return data

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user_rec = self.env['res.users'].browse(self._uid)
        erp_manager_id = self.env['ir.model.data'].get_object_reference('base',
                                                                        'group_erp_manager')[1]
        if user_rec and erp_manager_id not in user_rec.groups_id.ids:
            if user_rec.store_ids:
                args += ['|', ('store_id', 'in', user_rec.store_ids.ids), ('store_id', '=', False)]
            res = super(pos_order, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        else:
            res = super(pos_order, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        return res

    # @api.one
    def get_timezone_date_order(self):
        if self.env.user.tz:
            tz = pytz.timezone(self.env.user.tz)
        else:
            tz = pytz.utc
        c_time = datetime.now(tz)
        hour_tz = int(str(c_time)[-5:][:2])
        min_tz = int(str(c_time)[-5:][3:])
        sign = str(c_time)[-6][:1]
        if sign == '+':
            date_order = self.date_order + timedelta(hours=hour_tz, minutes=min_tz)
        if sign == '-':
            date_order = self.date_order - timedelta(hours=hour_tz, minutes=min_tz)
        return date_order

    # @api.one
    def update_delivery_date(self, reserve_delivery_date, draft_delivery_order=False):
        if not draft_delivery_order:
            res = self.write({'reserve_delivery_date': datetime.strptime(reserve_delivery_date, '%Y-%m-%d')})
        else:
            res = self.write({'delivery_date': reserve_delivery_date})
        if res:
            return self.read()[0]
        return False

    # @api.multi
    def write(self, vals):
        res = super(pos_order, self).write(vals)
        if vals.get('delivery_type') or vals.get('delivery_user_id') or vals.get('delivery_address') or \
                vals.get('delivery_date') or vals.get('delivery_time'):
            delivery_notif = []
            pos_session_ids = self.env['pos.session'].search([('state', '=', 'opened')])
            for session in pos_session_ids:
                delivery_notif.append([(self._cr.dbname, 'lock.data', session.user_id.id),
                                       {'delivery_pos_order': self.read()}])
            self.env['bus.bus'].sendmany(delivery_notif)

        if vals.get('amount_due') and vals.get('amount_due') > 0.0:
            notifications = []
            notify_users = []
            order_id = self.browse(vals.get('old_order_id'))
            order_user = self.env['res.users'].browse(vals.get('user_id'))
            users = self.env['res.users'].search([])
            if order_id.user_id == order_id.salesman_id:
                for user_main in users:
                    if user_main.sales_persons:
                        for user in user_main.sales_persons:
                            if user.id == order_user.id:
                                session = self.env['pos.session'].search([('user_id', '=', user_main.id)], limit=1)
                                if session:
                                    notify_users.append(session.user_id.id)
            else:
                notify_users += (order_id.salesman_id.id, order_id.user_id.id)
            for user in notify_users:
                notifications.append([(self._cr.dbname, 'lock.data', user),
                                      {'edited_pos_order': order_id.read()}])
            self.env['bus.bus'].sendmany(notifications)

        for each in self:
            if vals.get('state') == 'paid' and each.reserved and each.picking_id:
                picking_id = each.picking_id.copy()
                picking_type_id = self.env['stock.picking.type'].search([
                    ('warehouse_id', '=', each.picking_id.picking_type_id.warehouse_id.id), ('code', '=', 'outgoing')],
                    limit=1)
                if picking_type_id:
                    location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()
                    name = self.env['stock.picking.type'].browse(
                        vals.get('picking_type_id', picking_type_id.id)).sequence_id.next_by_id()
                    picking_id.write(
                        {'picking_type_id': picking_type_id.id, 'location_id': each.picking_id.location_dest_id.id,
                         'location_dest_id': location_dest_id.id, 'name': name, 'origin': each.name})
                    #                     if picking_id.pack_operation_pack_ids:
                    #                         picking_id.pack_operation_pack_ids.write({'location_id':each.picking_id.location_dest_id.id,
                    #                                       'location_dest_id': location_dest_id.id})
                    if picking_id.move_lines:
                        picking_id.move_lines.write({'location_id': each.picking_id.location_dest_id.id,
                                                     'location_dest_id': location_dest_id.id, 'origin': each.name})
                    picking_id.action_confirm()
                    picking_id.action_assign()
                    for each in picking_id.move_lines:
                        each.write({'quantity_done': each.product_uom_qty})
                    picking_id.button_validate()
                    stock_transfer_id = self.env['stock.immediate.transfer'].search([('pick_ids', '=', picking_id.id)],
                                                                                    limit=1).process()
                    if stock_transfer_id:
                        stock_transfer_id.process()
                    query = ''' UPDATE pos_order SET unreserved=True,
                       picking_id='%s'
                       WHERE id=%s''' % (picking_id.id, each.id)
                    self._cr.execute(query)
                    each.write({'picking_id': picking_id.id})
        return res

    # @api.multi
    # def action_pos_order_paid(self):
    #     if self.order_make_picking and not self.test_paid() and not self.picking_id:
    #         self.create_picking()
    #     if not self.test_paid():
    #         raise UserError(_("Order is not paid."))
    #     else:
    #         self.write({'state': 'paid'})
    #         # custom code
    #         notifications = []
    #         notify_users = []
    #         notifications_for_products = []
    #         for each_pos_order in self:
    #             order_id = self.browse(each_pos_order.id)
    #             order_user = self.env['res.users'].browse(order_id.user_id.id)
    #             if order_id.salesman_id:
    #                 notify_users += (order_id.salesman_id.id, order_id.user_id.id)
    #                 config_obj = self.env['pos.config'].search([])
    #                 for each in config_obj:
    #                     orderlines = []
    #                     for line in order_id.lines:
    #                         orderlines.append(line.read())
    #                     session_id = self.env['pos.session'].search(
    #                         [('config_id', '=', each.id), ('state', '=', 'opened')], limit=1)
    #                     notifications_for_products.append(((self._cr.dbname, 'lock.data', session_id.user_id.id),
    #                                                        ('update_product_screen', orderlines)))
    #             self.env['bus.bus'].sendmany(notifications_for_products)
    #             for user in notify_users:
    #                 notifications.append([(self._cr.dbname, 'lock.data', user),
    #                                       {'sync_order_paid': order_id.read()}])
    #             self.env['bus.bus'].sendmany(notifications)
    #
    #         if not self.order_make_picking:
    #             picking_id_cust = False
    #             location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()
    #             if self.order_status in ['full', 'partial'] or self.order_booked:
    #                 for line in self.lines:
    #                     if line.product_id.type != 'service' and not line.cancel_item and line.line_status == 'nothing':
    #                         # customer delivery order
    #                         picking_type_out = self.env['stock.picking.type'].search([
    #                             ('warehouse_id', '=', self.picking_id.picking_type_id.warehouse_id.id),
    #                             ('code', '=', 'outgoing')], limit=1)
    #                         if picking_type_out:
    #                             picking_vals_rev = {
    #                                 'name': picking_type_out.sequence_id.next_by_id(),
    #                                 'picking_type_id': picking_type_out.id,
    #                                 'location_id': self.config_id.reserve_stock_location_id.id,
    #                                 'location_dest_id': location_dest_id.id,
    #                                 'state': 'draft',
    #                                 'origin': self.name
    #                             }
    #                             if not picking_id_cust:
    #                                 picking_id_cust = self.env['stock.picking'].create(picking_vals_rev)
    #                             move_id = self.env['stock.move'].create({
    #                                 'product_id': line.product_id.id,
    #                                 'name': line.product_id.name,
    #                                 'product_uom_qty': line.qty,
    #                                 'location_id': self.config_id.reserve_stock_location_id.id,
    #                                 'location_dest_id': location_dest_id.id,
    #                                 'product_uom': line.product_id.uom_id.id,
    #                                 'origin': self.name,
    #                                 'picking_id': picking_id_cust.id
    #                             })
    #                 if picking_id_cust and picking_id_cust.move_lines:
    #                     picking_id_cust.action_confirm()
    #                     for each in picking_id_cust.move_lines:
    #                         each.write({'quantity_done': each.product_uom_qty})
    #                     picking_id_cust.button_validate()
    #                     stock_transfer_id = self.env['stock.immediate.transfer'].search(
    #                         [('pick_ids', '=', picking_id_cust.id)], limit=1)
    #                     if stock_transfer_id:
    #                         stock_transfer_id.process()
    #                     self.with_context({'out_order': True}).write(
    #                         {'picking_id': picking_id_cust.id, 'unreserved': True})
    #                 elif picking_id_cust:
    #                     picking_id_cust.unlink()
    #             return self.create_picking()

    # @api.model
    # def create_from_ui(self, orders):
    #     # Keep only new orders
    #     submitted_references = [o['data']['name'] for o in orders]
    #     pos_order = self.search([('pos_reference', 'in', submitted_references)])
    #     existing_orders = pos_order.read(['pos_reference'])
    #     existing_references = set([o['pos_reference'] for o in existing_orders])
    #     orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
    #     order_ids = []
    #
    #     for tmp_order in orders_to_save:
    #         # credit_details = tmp_order['data'].get('credit_detail')
    #         # if credit_details:
    #         #     self.env['account.invoice'].get_credit_info(credit_details)
    #         to_invoice = tmp_order['to_invoice']
    #         order = tmp_order['data']
    #         if to_invoice:
    #             self._match_payment_to_invoice(order)
    #         pos_order = self._process_order(order)
    #         # create giftcard record
    #         if order.get('giftcard'):
    #             for create_details in order.get('giftcard'):
    #                 vals = {
    #                     'card_no': create_details.get('giftcard_card_no'),
    #                     'card_value': create_details.get('giftcard_amount'),
    #                     'customer_id': create_details.get('giftcard_customer') or False,
    #                     'expire_date': datetime.strptime(create_details.get('giftcard_expire_date'),
    #                                                      '%Y/%m/%d').strftime('%Y-%m-%d'),
    #                     'card_type': create_details.get('card_type'),
    #                 }
    #                 self.env['aspl.gift.card'].create(vals)
    #
    #         #  create redeem giftcard for use
    #         if order.get('redeem') and pos_order:
    #             for redeem_details in order.get('redeem'):
    #                 redeem_vals = {
    #                     'pos_order_id': pos_order.id,
    #                     'order_date': pos_order.date_order,
    #                     'customer_id': redeem_details.get('card_customer_id') or False,
    #                     'card_id': redeem_details.get('redeem_card_no'),
    #                     'amount': redeem_details.get('redeem_card_amount'),
    #                 }
    #                 use_giftcard = self.env['aspl.gift.card.use'].create(redeem_vals)
    #                 if use_giftcard:
    #                     use_giftcard.card_id.write(
    #                         {'card_value': use_giftcard.card_id.card_value - use_giftcard.amount})
    #
    #         # recharge giftcard
    #         if order.get('recharge'):
    #             for recharge_details in order.get('recharge'):
    #                 recharge_vals = {
    #                     'user_id': pos_order.user_id.id,
    #                     'recharge_date': pos_order.date_order,
    #                     'customer_id': recharge_details.get('card_customer_id') or False,
    #                     'card_id': recharge_details.get('recharge_card_id'),
    #                     'amount': recharge_details.get('recharge_card_amount'),
    #                 }
    #                 recharge_giftcard = self.env['aspl.gift.card.recharge'].create(recharge_vals)
    #                 if recharge_giftcard:
    #                     recharge_giftcard.card_id.write(
    #                         {'card_value': recharge_giftcard.card_id.card_value + recharge_giftcard.amount})
    #         if order.get('voucher'):
    #             for voucher in order.get('voucher'):
    #                 vals = {
    #                     'voucher_id': voucher.get('id') or False,
    #                     'voucher_code': voucher.get('voucher_code'),
    #                     'user_id': voucher.get('create_uid')[0],
    #                     'customer_id': order.get('partner_id'),
    #                     'order_name': pos_order.name,
    #                     'order_amount': pos_order.amount_total,
    #                     'voucher_amount': voucher.get('voucher_amount'),
    #                     'used_date': datetime.now(),
    #                 }
    #                 self.env['aspl.gift.voucher.redeem'].create(vals)
    #         if pos_order:
    #             pos_line_obj = self.env['pos.order.line']
    #             to_be_returned_items = {}
    #             to_be_cancelled_items = {}
    #             for line in order.get('lines'):
    #                 if line[2].get('cancel_process'):
    #                     if line[2].get('product_id') in to_be_cancelled_items:
    #                         to_be_cancelled_items[line[2].get('product_id')] = to_be_cancelled_items[
    #                                                                                line[2].get('product_id')] + line[
    #                                                                                2].get('qty')
    #                     else:
    #                         to_be_cancelled_items.update({line[2].get('product_id'): line[2].get('qty')})
    #                 if line[2].get('return_process'):
    #                     if line[2].get('product_id') in to_be_returned_items:
    #                         to_be_returned_items[line[2].get('product_id')] = to_be_returned_items[
    #                                                                               line[2].get('product_id')] + line[
    #                                                                               2].get('qty')
    #                     else:
    #                         to_be_returned_items.update({line[2].get('product_id'): line[2].get('qty')})
    #             for line in order.get('lines'):
    #                 for item_id in to_be_cancelled_items:
    #                     cancel_lines = []
    #                     if line[2].get('cancel_process'):
    #                         cancel_lines = self.browse([line[2].get('cancel_process')[0]]).lines
    #                     for origin_line in cancel_lines:
    #                         if to_be_cancelled_items[item_id] == 0:
    #                             continue
    #                         if origin_line.qty > 0 and item_id == origin_line.product_id.id:
    #                             if (to_be_cancelled_items[item_id] * -1) >= origin_line.qty:
    #                                 ret_from_line_qty = 0
    #                                 to_be_cancelled_items[item_id] = to_be_cancelled_items[item_id] + origin_line.qty
    #                             else:
    #                                 ret_from_line_qty = to_be_cancelled_items[item_id] + origin_line.qty
    #                                 to_be_cancelled_items[item_id] = 0
    #                             origin_line.write({'qty': ret_from_line_qty})
    #                 for item_id in to_be_returned_items:
    #                     if line[2].get('return_process'):
    #                         for origin_line in self.browse([line[2].get('return_process')[0]]).lines:
    #                             if to_be_returned_items[item_id] == 0:
    #                                 continue
    #                             if origin_line.return_qty > 0 and item_id == origin_line.product_id.id:
    #                                 if (to_be_returned_items[item_id] * -1) >= origin_line.return_qty:
    #                                     ret_from_line_qty = 0
    #                                     to_be_returned_items[item_id] = to_be_returned_items[
    #                                                                         item_id] + origin_line.return_qty
    #                                 else:
    #                                     ret_from_line_qty = to_be_returned_items[item_id] + origin_line.return_qty
    #                                     to_be_returned_items[item_id] = 0
    #                                 origin_line.write({'return_qty': ret_from_line_qty});
    #         order_ids.append(pos_order.id)
    #
    #         try:
    #             pos_order.action_pos_order_paid()
    #         except psycopg2.OperationalError:
    #             # do not hide transactional errors, the order(s) won't be saved!
    #             raise
    #         except Exception as e:
    #             _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
    #
    #         if to_invoice:
    #             pos_order.action_pos_order_invoice()
    #             pos_order.invoice_id.sudo().action_invoice_open()
    #             pos_order.account_move = pos_order.invoice_id.move_id
    #     return order_ids

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """Create account.bank.statement.lines from the dictionary given to the parent function.

        If the payment_line is an updated version of an existing one, the existing payment_line will first be
        removed before making a new one.
        :param pos_order: dictionary representing the order.
        :type pos_order: dict.
        :param order: Order object the payment lines should belong to.
        :type order: pos.order
        :param pos_session: PoS session the order was created in.
        :type pos_session: pos.session
        :param draft: Indicate that the pos_order is not validated yet.
        :type draft: bool.
        """
        prec_acc = order.pricelist_id.currency_id.decimal_places
        order_bank_statement_lines = self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
        order_bank_statement_lines.unlink()
        for payments in pos_order['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
                order.add_payment(self._payment_fields(order, payments[2]))

        order.amount_paid = sum(order.payment_ids.mapped('amount'))
        if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
            # if pos_order.get('rounding'):
            #     cash_journal_id = pos_session.cash_journal_id.id
            #     if not cash_journal_id:
            #         # Select for change one of the cash journals used in this
            #         # paymen
            #         cash_journal = self.env['account.journal'].search([
            #             ('type', '=', 'cash'),
            #             ('id', 'in', list(journal_ids)),
            #         ], limit=1)
            #         if not cash_journal:
            #             cash_journal = [statement.journal_id for statement in pos_session.statement_ids if
            #                             statement.journal_id.type == 'cash']
            #             if not cash_journal:
            #                 raise UserError(
            #                     _("No cash statement found for this session. Unable to record returned cash."))
            #         cash_journal_id = cash_journal[0].id
            #         order.add_payment({
            #             'amount': -pos_order['data']['amount_return'],
            #             'payment_date': fields.Datetime.now(),
            #             'payment_name': _('return'),
            #             'payment_method_id': cash_journal_id.id,
            #         })
            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
            return_payment_vals = {
                'name': _('return'),
                'pos_order_id': order.id,
                'amount': -pos_order['amount_return'],
                'payment_date': fields.Date.context_today(self),
                'payment_method_id': cash_payment_method.id,
            }
            order.add_payment(return_payment_vals)
        # if pos_order.get('rounding'):
        #     rounding_journal_id = order.session_id.config_id.rounding_journal_id
        #     rounding_payment_method_id = self.env['pos.payment.method'].search([
        #         ('jr_use_for', '=', 'rounding'),
        #     ], limit=1)
        #     if rounding_journal_id:
        #         order.add_payment({
        #             'amount': pos_order['rounding'] * -1,
        #             'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        #             'name': _('Rounding'),
        #             'payment_method_id': rounding_payment_method_id.id,
        #             'pos_order_id': order.id,
        #         })

    @api.model
    def wallet_management(self, order, res):
        if order.get('wallet_type'):
            if order.get('change_amount_for_wallet'):
                session_id = res.session_id
                cash_register_id = session_id.cash_register_id
                # if cash_register_id:
                #     cash_bocx_in_obj = self.env['cash.box.out'].create({
                #         'name': 'Credit',
                #         'amount': order.get('change_amount_for_wallet')
                #     })
                #     cash_bocx_in_obj._run(cash_register_id)
                vals = {
                    'customer_id': order.get('partner_id') or res.partner_id.id or False,
                    'type': order.get('wallet_type'),
                    'order_id': res.id,
                    'credit': order.get('change_amount_for_wallet'),
                    'cashier_id': order.get('user_id'),
                }
                self.env['wallet.management'].create(vals)
            if order.get('used_amount_from_wallet'):
                vals = {
                    'customer_id': order.get('partner_id') or res.partner_id.id or False,
                    'type': order.get('wallet_type'),
                    'order_id': res.id,
                    'debit': order.get('used_amount_from_wallet'),
                    'cashier_id': order.get('user_id'),
                }
                self.env['wallet.management'].create(vals)

    @api.model
    def _process_order(self, order, draft, existing_order):
        order = order['data']
        if order.get('old_order_id'):
            existing_order = self.browse([order.get('old_order_id')])

        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            order['pos_session_id'] = self._get_valid_session(order).id

        if order.get('draft_order'):
            if not order.get('old_order_id'):
                order.pop('draft_order')

        pos_order = False
        if not existing_order:
            pos_order = self.create(self._order_fields(order))
            self.wallet_management(order, pos_order)
        else:
            pos_order = existing_order
            pos_order.lines.unlink()
            order['user_id'] = pos_order.user_id.id
            pos_order.write(self._order_fields(order))

        # Gift Card Code Start
        if order.get('giftcard'):
            for create_details in order.get('giftcard'):
                expiry_date = datetime.strptime(create_details.get('giftcard_expire_date'), '%Y-%m-%d').strftime(
                    '%Y-%m-%d')
                vals = {
                    'card_no': create_details.get('giftcard_card_no'),
                    'card_value': create_details.get('giftcard_amount'),
                    'customer_id': create_details.get('giftcard_customer') or False,
                    'expire_date': expiry_date,
                    'card_type': create_details.get('card_type'),
                }
                self.env['aspl.gift.card'].create(vals)

        #  create redeem giftcard for use
        if order.get('redeem') and pos_order:
            for redeem_details in order.get('redeem'):
                redeem_vals = {
                    'pos_order_id': pos_order.id,
                    'order_date': pos_order.date_order,
                    'customer_id': redeem_details.get('card_customer_id') or False,
                    'card_id': redeem_details.get('redeem_card_no'),
                    'amount': redeem_details.get('redeem_card_amount'),
                }
                use_giftcard = self.env['aspl.gift.card.use'].create(redeem_vals)
                if use_giftcard:
                    use_giftcard.card_id.write({'card_value': use_giftcard.card_id.card_value - use_giftcard.amount})

        # recharge giftcard
        if order.get('recharge'):
            for recharge_details in order.get('recharge'):
                recharge_vals = {
                    'user_id': pos_order.user_id.id,
                    'recharge_date': pos_order.date_order,
                    'customer_id': recharge_details.get('card_customer_id') or False,
                    'card_id': recharge_details.get('recharge_card_id'),
                    'amount': recharge_details.get('recharge_card_amount'),
                }
                recharge_giftcard = self.env['aspl.gift.card.recharge'].create(recharge_vals)
                if recharge_giftcard:
                    recharge_giftcard.card_id.write(
                        {'card_value': recharge_giftcard.card_id.card_value + recharge_giftcard.amount})
        # Gift Card Code End

        # Gift voucher Code Start
        if order.get('voucher'):
            for voucher in order.get('voucher'):
                vals = {
                    'voucher_id': voucher.get('id') or False,
                    'voucher_code': voucher.get('voucher_code'),
                    'user_id': voucher.get('create_uid')[0],
                    'customer_id': order.get('partner_id'),
                    'order_name': pos_order.name,
                    'order_amount': pos_order.amount_total,
                    'voucher_amount': voucher.get('voucher_amount'),
                    'used_date': datetime.now(),
                }
                self.env['aspl.gift.voucher.redeem'].create(vals)
        # Gift voucher End

        if pos_order:
            # Loyalty Point code Start            
            if pos_order and order.get('increment_number') and pos_order.session_id.config_id.generate_token:
                pos_order.session_id.update({'increment_number': order.get('increment_number')})
            if pos_order.session_id.config_id.enable_pos_loyalty and pos_order.partner_id:
                loyalty_settings = self.env['loyalty.config.settings'].load_loyalty_config_settings()
                if loyalty_settings and loyalty_settings[0]:
                    if loyalty_settings[0].get('points_based_on') and order.get('loyalty_earned_point'):
                        point_vals = {
                            'pos_order_id': pos_order.id,
                            'partner_id': pos_order.partner_id.id,
                            'points': order.get('loyalty_earned_point'),
                            'amount_total': (float(order.get('loyalty_earned_point')) * loyalty_settings[0].get(
                                'to_amount')) / loyalty_settings[0].get('points')
                        }
                        loyalty = self.env['loyalty.point'].create(point_vals)
                        if loyalty and pos_order.partner_id.send_loyalty_mail:
                            try:
                                template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
                                                                                             'email_template_pos_loyalty')
                                template_obj = self.env['mail.template'].browse(template_id[1])
                                template_obj.send_mail(loyalty.id, force_send=True, raise_exception=True)
                            except Exception as e:
                                _logger.error('Unable to send email for order %s', e)

                    if order.get('loyalty_redeemed_point'):
                        redeemed_vals = {
                            'redeemed_pos_order_id': pos_order.id,
                            'partner_id': pos_order.partner_id.id,
                            'redeemed_amount_total': self._calculate_amount_total_by_points(loyalty_settings, order.get(
                                'loyalty_redeemed_point')),
                            'redeemed_point': order.get('loyalty_redeemed_point'),
                        }
                        self.env['loyalty.point.redeem'].create(redeemed_vals)
            if order.get('customer_email'):
                try:
                    template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
                                                                                 'email_template_pos_ereceipt')
                    template_obj = self.env['mail.template'].browse(template_id[1])
                    template_obj.send_mail(pos_order.id, force_send=True, raise_exception=True)
                except Exception as e:
                    _logger.error('Unable to send email for order %s', e)
                # if pos_order and order.get('increment_number') and pos_order.session_id.config_id.generate_token:
                #     pos_order.session_id.update({'increment_number':order.get('increment_number')})
                # if pos_order.rest_table_reservation_id:
                #     table_record = self.env['restaurant.table.reservation'].search([('id','=',pos_order.rest_table_reservation_id.id)])
                #     if table_record:
                #         table_record.state = 'done'
            # Loyalty Point code End

            # Send Cutomer Email
            # if order.get('customer_email'):
            #     try:
            #         template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance', 'email_template_pos_ereceipt')
            #         template_obj = self.env['mail.template'].browse(template_id[1])
            #         template_obj.send_mail(pos_order.id,force_send=True, raise_exception=True)
            #     except Exception as e:
            #         _logger.error('Unable to send email for order %s',e)
            #     if pos_order and order.get('increment_number') and pos_order.session_id.config_id.generate_token:
            #         pos_order.session_id.update({'increment_number':order.get('increment_number')})
            #     if pos_order.rest_table_reservation_id:
            #         table_record = self.env['restaurant.table.reservation'].search([('id','=',pos_order.rest_table_reservation_id.id)])
            #         if table_record:
            #             table_record.state = 'done'

        self._process_payment_lines(order, pos_order, pos_session, draft)

        if not draft:
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

        if pos_order.to_invoice and pos_order.state == 'paid':
            pos_order.action_pos_order_invoice()
        if (order.get('is_kitchen_order')):
            self.broadcast_order_data(True)
        return pos_order.id

    # @api.model
    # def _process_order(self, order, draft, existing_order):
    #     if not order.get('draft_order') and not order.get('old_order_id'):
    #         res = super(pos_order, self)._process_order(order, draft, existing_order)
    #         order = order['data']
    #         res = self.browse([res])
    #         # if res:
    #         #     self.wallet_management(order, res)
    #         print ("\n\n order======>",order)
    #
    #         # create giftcard record
    #         if order.get('giftcard'):
    #             for create_details in order.get('giftcard'):
    #                 expiry_date = datetime.strptime(create_details.get('giftcard_expire_date'),
    #                                                 '%Y/%m/%d').strftime('%Y-%m-%d')
    #                 vals = {
    #                     'card_no': create_details.get('giftcard_card_no'),
    #                     'card_value': create_details.get('giftcard_amount'),
    #                     'customer_id': create_details.get('giftcard_customer') or False,
    #                     'expire_date': expiry_date,
    #                     'card_type': create_details.get('card_type'),
    #                 }
    #                 self.env['aspl.gift.card'].create(vals)
    #
    #         #  create redeem giftcard for use
    #         print("calllll")
    #         if order.get('redeem') and res:
    #             print("\n\n jgsdfsgfshfgf======>", res)
    #             for redeem_details in order.get('redeem'):
    #                 redeem_vals = {
    #                     'pos_order_id': res.id,
    #                     'order_date': res.date_order,
    #                     'customer_id': redeem_details.get('card_customer_id') or False,
    #                     'card_id': redeem_details.get('redeem_card_no'),
    #                     'amount': redeem_details.get('redeem_card_amount'),
    #                 }
    #                 use_giftcard = self.env['aspl.gift.card.use'].create(redeem_vals)
    #                 if use_giftcard:
    #                     use_giftcard.card_id.write(
    #                         {'card_value': use_giftcard.card_id.card_value - use_giftcard.amount})
    #
    #         # recharge giftcard
    #         if order.get('recharge'):
    #             for recharge_details in order.get('recharge'):
    #                 recharge_vals = {
    #                     'user_id': res.user_id.id,
    #                     'recharge_date': res.date_order,
    #                     'customer_id': recharge_details.get('card_customer_id') or False,
    #                     'card_id': recharge_details.get('recharge_card_id'),
    #                     'amount': recharge_details.get('recharge_card_amount'),
    #                 }
    #                 recharge_giftcard = self.env['aspl.gift.card.recharge'].create(recharge_vals)
    #                 if recharge_giftcard:
    #                     recharge_giftcard.card_id.write(
    #                         {'card_value': recharge_giftcard.card_id.card_value + recharge_giftcard.amount})
    #         if order.get('voucher'):
    #             for voucher in order.get('voucher'):
    #                 vals = {
    #                     'voucher_id': voucher.get('id') or False,
    #                     'voucher_code': voucher.get('voucher_code'),
    #                     'user_id': voucher.get('create_uid')[0],
    #                     'customer_id': order.get('partner_id'),
    #                     'order_name': res.name,
    #                     'order_amount': res.amount_total,
    #                     'voucher_amount': voucher.get('voucher_amount'),
    #                     'used_date': datetime.now(),
    #                 }
    #                 self.env['aspl.gift.voucher.redeem'].create(vals)
    #
    #         if res.session_id.config_id.enable_pos_loyalty and res.partner_id:
    #             loyalty_settings = self.env['loyalty.config.settings'].load_loyalty_config_settings()
    #             if loyalty_settings and loyalty_settings[0]:
    #                 if loyalty_settings[0].get('points_based_on') and order.get('loyalty_earned_point'):
    #                     point_vals = {
    #                         'pos_order_id': res.id,
    #                         'partner_id': res.partner_id.id,
    #                         'points': order.get('loyalty_earned_point'),
    #                         'amount_total': (float(order.get('loyalty_earned_point')) * loyalty_settings[0].get(
    #                             'to_amount')) / loyalty_settings[0].get('points')
    #                     }
    #                     loyalty = self.env['loyalty.point'].create(point_vals)
    #                     if loyalty and res.partner_id.send_loyalty_mail:
    #                         try:
    #                             template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
    #                                                                                          'email_template_pos_loyalty')
    #                             template_obj = self.env['mail.template'].browse(template_id[1])
    #                             template_obj.send_mail(loyalty.id, force_send=True, raise_exception=True)
    #                         except Exception as e:
    #                             _logger.error('Unable to send email for order %s', e)
    #
    #                 if order.get('loyalty_redeemed_point'):
    #                     redeemed_vals = {
    #                         'redeemed_pos_order_id': res.id,
    #                         'partner_id': res.partner_id.id,
    #                         'redeemed_amount_total': self._calculate_amount_total_by_points(loyalty_settings, order.get(
    #                             'loyalty_redeemed_point')),
    #                         'redeemed_point': order.get('loyalty_redeemed_point'),
    #                     }
    #                     self.env['loyalty.point.redeem'].create(redeemed_vals)
    #
    #         return res.id

    # @api.model
    # def _process_order(self, order):
    #     pos_line_obj = self.env['pos.order.line']
    #     res = False;
    #     draft_order_id = order.get('old_order_id')
    #     move_obj = self.env['stock.move']
    #     picking_obj = self.env['stock.picking']
    #     stock_imm_tra_obj = self.env['stock.immediate.transfer']
    #     picking_type_id = False
    #     picking_id_cust = False
    #     picking_id_rev = False
    #     if order.get('draft_order'):
    #         if not draft_order_id:
    #             order.pop('draft_order')
    #             order_id = self.create(self._order_fields(order))
    #             res = order_id
    #         else:
    #             order_id = draft_order_id
    #             pos_line_ids = pos_line_obj.search([('order_id', '=', order_id)])
    #             if pos_line_ids:
    #                 self._cr.execute(
    #                     "DELETE FROM pos_order_line where id in (%s) " % ','.join(map(str, pos_line_ids._ids)))
    #             self.write([order_id],
    #                        {'lines': order['lines'],
    #                         'partner_id': order.get('partner_id')})
    #             res = order_id
    #     if not order.get('draft_order') and draft_order_id:
    #         order_id = draft_order_id
    #         order_obj = self.browse(order_id)
    #         pos_line_ids = pos_line_obj.search([('order_id', '=', order_id)])
    #         if pos_line_ids:
    #             self._cr.execute("DELETE FROM pos_order_line where id in (%s) " % ','.join(map(str, pos_line_ids._ids)))
    #         temp = order.copy()
    #         temp.pop('statement_ids', None)
    #         temp.pop('name', None)
    #         temp.update({
    #             'date_order': order.get('creation_date')
    #         })
    #         warehouse_id = self.env['stock.warehouse'].search([
    #             ('lot_stock_id', '=', order_obj.config_id.stock_location_id.id)], limit=1)
    #         location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()
    #         if warehouse_id:
    #             picking_type_id = self.env['stock.picking.type'].search([
    #                 ('warehouse_id', '=', warehouse_id.id), ('code', '=', 'internal')])
    #         for line in order.get('lines'):
    #             prod_id = self.env['product.product'].browse(line[2].get('product_id'))
    #             prod_dict = line[2]
    #             if prod_id.type != 'service' and prod_dict and prod_dict.get('cancel_item'):
    #                 # customer delivery order
    #                 picking_type_out = self.env['stock.picking.type'].search([
    #                     ('warehouse_id', '=', order_obj.picking_id.picking_type_id.warehouse_id.id),
    #                     ('code', '=', 'outgoing')], limit=1)
    #                 if picking_type_out:
    #                     picking_id_cust = picking_obj.create({
    #                         'name': picking_type_out.sequence_id.next_by_id(),
    #                         'picking_type_id': picking_type_out.id,
    #                         'location_id': order_obj.config_id.reserve_stock_location_id.id,
    #                         'location_dest_id': location_dest_id.id,
    #                         'state': 'draft',
    #                         'origin': order_obj.name
    #                     })
    #                 if order_obj.picking_id:
    #                     # unreserve order
    #                     picking_id_rev = picking_obj.create({
    #                         'name': picking_type_out.sequence_id.next_by_id(),
    #                         'picking_type_id': order_obj.picking_id.picking_type_id.id,
    #                         'location_id': order_obj.config_id.reserve_stock_location_id.id,
    #                         'location_dest_id': order_obj.config_id.stock_location_id.id,
    #                         'state': 'draft',
    #                         'origin': order_obj.name
    #                     })
    #                     if prod_dict.get('consider_qty') and not order_obj.order_status == 'partial' and not order.get(
    #                             'reserved'):
    #                         move_obj.create({
    #                             'product_id': prod_id.id,
    #                             'name': prod_id.name,
    #                             'product_uom_qty': prod_dict.get('consider_qty'),
    #                             'location_id': order_obj.config_id.reserve_stock_location_id.id,
    #                             'location_dest_id': location_dest_id.id,
    #                             'product_uom': prod_id.uom_id.id,
    #                             'origin': order_obj.name,
    #                             'picking_id': picking_id_cust.id
    #                         })
    #                     if prod_dict.get('cancel_qty'):
    #                         move_obj.create({
    #                             'product_id': prod_id.id,
    #                             'name': prod_id.name,
    #                             'product_uom_qty': abs(prod_dict.get('cancel_qty')),
    #                             'location_id': order_obj.config_id.reserve_stock_location_id.id,
    #                             'location_dest_id': order_obj.config_id.stock_location_id.id,
    #                             'product_uom': prod_id.uom_id.id,
    #                             'origin': order_obj.name,
    #                             'picking_id': picking_id_rev.id
    #                         })
    #         if picking_id_cust and picking_id_cust.move_lines:
    #             picking_id_cust.action_confirm()
    #             picking_id_cust.action_assign()
    #             for each in picking_id_cust.move_lines:
    #                 each.write({'quantity_done': each.product_uom_qty})
    #             picking_id_cust.button_validate()
    #             stock_transfer_id = stock_imm_tra_obj.search([('pick_ids', '=', picking_id_cust.id)], limit=1)
    #             if stock_transfer_id:
    #                 stock_transfer_id.process()
    #             order_obj.with_context({'out_order': True}).write(
    #                 {'picking_id': picking_id_cust.id, 'unreserved': True})
    #         elif picking_id_cust:
    #             picking_id_cust.unlink()
    #         if picking_id_rev and picking_id_rev.move_lines:
    #             picking_id_rev.action_confirm()
    #             picking_id_rev.action_assign()
    #             for each in picking_id_rev.move_lines:
    #                 each.write({'quantity_done': each.product_uom_qty})
    #             picking_id_rev.button_validate()
    #             stock_transfer_id = stock_imm_tra_obj.search([('pick_ids', '=', picking_id_rev.id)], limit=1)
    #             if stock_transfer_id:
    #                 stock_transfer_id.process()
    #             order_obj.with_context({'out_order': True}).write({'picking_id': picking_id_rev.id, 'unreserved': True})
    #         elif picking_id_rev:
    #             picking_id_rev.unlink()
    #         total_price = 0.0
    #         for line in temp.get('lines'):
    #             linedict = line[2]
    #             if order_obj.session_id.config_id.prod_for_payment.id == linedict.get('product_id'):
    #                 if line in temp.get('lines'):
    #                     temp.get('lines').remove(line)
    #             if order_obj.session_id.config_id.refund_amount_product_id.id == linedict.get('product_id'):
    #                 if line in temp.get('lines'):
    #                     temp.get('lines').remove(line)
    #             if order_obj.session_id.config_id.prod_for_credit_payment.id == linedict.get('product_id'):
    #                 if line in temp.get('lines'):
    #                     temp.get('lines').remove(line)
    #         total_price += sum([line[2].get('price_subtotal_incl') for line in temp.get('lines')])
    #         temp['amount_total'] = total_price
    #         order_obj.write(temp)
    #         for payments in order['statement_ids']:
    #             order_obj.with_context({'from_pos': True}).add_payment(self._payment_fields(payments[2]))
    #         session = self.env['pos.session'].browse(order['pos_session_id'])
    #         if session.sequence_number <= order['sequence_number']:
    #             session.write({'sequence_number': order['sequence_number'] + 1})
    #             session.refresh()
    #
    #         if not float_is_zero(order['amount_return'], self.env['decimal.precision'].precision_get('Account')):
    #             cash_journal = session.cash_journal_id
    #             if not cash_journal:
    #                 cash_journal_ids = session.statement_ids.filtered(lambda st: st.journal_id.type == 'cash')
    #                 if not len(cash_journal_ids):
    #                     raise Warning(_('error!'),
    #                                   _("No cash statement found for this session. Unable to record returned cash."))
    #                 cash_journal = cash_journal_ids[0].journal_id
    #             order_obj.with_context({'from_pos': True}).add_payment({
    #                 'amount': -order['amount_return'],
    #                 'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    #                 'payment_name': _('return'),
    #                 'journal': cash_journal.id,
    #             })
    #         res = order_obj
    #
    #     if not order.get('draft_order') and not draft_order_id:
    #         res = super(pos_order, self)._process_order(order)
    #         if res:
    #             if order.get('wallet_type'):
    #                 if order.get('change_amount_for_wallet'):
    #                     session_id = res.session_id
    #                     cash_register_id = session_id.cash_register_id
    #                     if not cash_register_id:
    #                         raise Warning(_('There is no cash register for this PoS Session'))
    #                     # cash_bocx_in_obj = self.env['cash.box.in'].create(
    #                     #     {'name': 'Credit', 'amount': order.get('change_amount_for_wallet')})
    #                     # cash_bocx_in_obj._run(cash_register_id)
    #                     vals = {
    #                         'customer_id': res.partner_id.id,
    #                         'type': order.get('wallet_type'),
    #                         'order_id': res.id,
    #                         'credit': order.get('change_amount_for_wallet'),
    #                         'cashier_id': order.get('user_id'),
    #                     }
    #                     self.env['wallet.management'].create(vals)
    #                 if order.get('used_amount_from_wallet'):
    #                     vals = {
    #                         'customer_id': res.partner_id.id,
    #                         'type': order.get('wallet_type'),
    #                         'order_id': res.id,
    #                         'debit': order.get('used_amount_from_wallet'),
    #                         'cashier_id': order.get('user_id'),
    #                     }
    #                     self.env['wallet.management'].create(vals)
    #         if res.reserved:
    #             res.do_internal_transfer()
    #     if res.session_id.config_id.enable_pos_loyalty and res.partner_id:
    #         loyalty_settings = self.env['loyalty.config.settings'].load_loyalty_config_settings()
    #         if loyalty_settings and loyalty_settings[0]:
    #             if loyalty_settings[0].get('points_based_on') and order.get('loyalty_earned_point'):
    #                 point_vals = {
    #                     'pos_order_id': res.id,
    #                     'partner_id': res.partner_id.id,
    #                     'points': order.get('loyalty_earned_point'),
    #                     'amount_total': (float(order.get('loyalty_earned_point')) * loyalty_settings[0].get(
    #                         'to_amount')) / loyalty_settings[0].get('points')
    #                 }
    #                 loyalty = self.env['loyalty.point'].create(point_vals)
    #                 if loyalty and res.partner_id.send_loyalty_mail:
    #                     try:
    #                         template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
    #                                                                                      'email_template_pos_loyalty')
    #                         template_obj = self.env['mail.template'].browse(template_id[1])
    #                         template_obj.send_mail(loyalty.id, force_send=True, raise_exception=False)
    #                     except Exception as e:
    #                         _logger.error('Unable to send email for order %s', e)
    #             if order.get('loyalty_redeemed_point'):
    #                 redeemed_vals = {
    #                     'redeemed_pos_order_id': res.id,
    #                     'partner_id': res.partner_id.id,
    #                     'redeemed_amount_total': self._calculate_amount_total_by_points(loyalty_settings, order.get(
    #                         'loyalty_redeemed_point')),
    #                     'redeemed_point': order.get('loyalty_redeemed_point'),
    #                 }
    #                 self.env['loyalty.point.redeem'].create(redeemed_vals)
    #     return res

    def _order_fields(self, ui_order):
        res = super(pos_order, self)._order_fields(ui_order)

        new_order_line = []
        process_line = partial(self.env['pos.order.line']._order_line_fields)
        order_lines = [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False
        if order_lines:
            for order_line in order_lines:
                #             new_order_line.append(order_line)
                if 'combo_ext_line_info' in order_line[2]:
                    order_line[2]['is_main_combo_product'] = True
                    own_pro_list = [process_line(l) for l in order_line[2]['combo_ext_line_info']] if order_line[2][
                        'combo_ext_line_info'] else False
                    if own_pro_list:
                        for own in own_pro_list:
                            own[2]['price_subtotal'] = 0
                            own[2]['price_subtotal_incl'] = 0
                            own[2]['is_combo_line'] = True
                            own[2]['combo_product_id'] = order_line[2]['product_id']
                            own[2]['tax_ids'] = [(6, 0, [])]
                            new_order_line.append(own)
                if order_line[2].get('modifier') == True:
                    order_line[2]['price_subtotal'] = 0
                    order_line[2]['price_subtotal_incl'] = 0
                new_order_line.append(order_line)

        res.update({
            'customer_email': ui_order.get('customer_email'),
            'note': ui_order.get('order_note') or False,
            # 'return_order': ui_order.get('return_order', ''),
            'back_order': ui_order.get('back_order', ''),
            'parent_return_order': ui_order.get('parent_return_order', ''),
            'return_seq': ui_order.get('return_seq', ''),
            # 'is_rounding': ui_order.get('is_rounding') or False,
            # 'rounding_option': ui_order.get('rounding_option') or False,
            # 'rounding': ui_order.get('rounding') or False,
            'change_amount_for_wallet': ui_order.get('change_amount_for_wallet') or 0.00,
            'amount_due': ui_order.get('amount_due'),
            'delivery_date': ui_order.get('delivery_date') or False,
            'delivery_time': ui_order.get('delivery_time') or False,
            'delivery_address': ui_order.get('delivery_address') or False,
            'delivery_charge_amt': ui_order.get('delivery_charge_amt') or False,
            'total_loyalty_earned_points': ui_order.get('loyalty_earned_point') or 0.00,
            'total_loyalty_earned_amount': ui_order.get('loyalty_earned_amount') or 0.00,
            'total_loyalty_redeem_points': ui_order.get('loyalty_redeemed_point') or 0.00,
            'total_loyalty_redeem_amount': ui_order.get('loyalty_redeemed_amount') or 0.00,
            'order_booked': ui_order.get('reserved') or False,
            'reserved': ui_order.get('reserved') or False,
            'reserve_delivery_date': ui_order.get('reserve_delivery_date') or False,
            'cancel_order': ui_order.get('cancel_order_ref') or False,
            'fresh_order': ui_order.get('fresh_order') or False,
            'partial_pay': ui_order.get('partial_pay') or False,
            'store_id': ui_order.get('store_id') or False,
            'rating': ui_order.get('rating'),
            'salesman_id': ui_order.get('salesman_id') or False,
            'order_make_picking': ui_order.get('order_make_picking') or False,
            'is_debit': ui_order.get('is_debit') or False,
            'delivery_type': ui_order.get('delivery_type'),
            'delivery_user_id': ui_order.get('delivery_user_id'),
            'order_on_debit': ui_order.get('order_on_debit'),
            'pos_normal_receipt_html': ui_order.get('pos_normal_receipt_html'),
            'pos_xml_receipt_html': ui_order.get('pos_xml_receipt_html'),
            'increment_number': ui_order.get('increment_number') or False,
            'table_ids': [(6, 0, ui_order.get('table_ids') or [])],
        })
        return res

    def set_pack_operation_lot(self, picking=None):
        """Set Serial/Lot number in pack operations to mark the pack operation done."""

        StockProductionLot = self.env['stock.production.lot']
        PosPackOperationLot = self.env['pos.pack.operation.lot']
        has_wrong_lots = False
        for order in self:
            for move in (picking or self.picking_id).move_lines:
                picking_type = (picking or self.picking_id).picking_type_id
                lots_necessary = True
                if picking_type:
                    lots_necessary = picking_type and picking_type.use_existing_lots
                qty = 0
                qty_done = 0
                pack_lots = []
                pos_pack_lots = PosPackOperationLot.search(
                    [('order_id', '=', order.id), ('product_id', '=', move.product_id.id)])
                pack_lot_names = [pos_pack.lot_name for pos_pack in pos_pack_lots]

                if pack_lot_names and lots_necessary:
                    for lot_name in list(set(pack_lot_names)):
                        stock_production_lot = StockProductionLot.search(
                            [('name', '=', lot_name), ('product_id', '=', move.product_id.id)])
                        if stock_production_lot:
                            if stock_production_lot.product_id.tracking == 'lot':
                                qty = pack_lot_names.count(lot_name)
                            #                                 qty = move.product_uom_qty
                            else:  # serial numbers
                                qty = 1.0
                            qty_done += qty
                            pack_lots.append({'lot_id': stock_production_lot.id, 'qty': qty})
                        else:
                            has_wrong_lots = True
                elif move.product_id.tracking == 'none' or not lots_necessary:
                    qty_done = move.product_uom_qty
                else:
                    has_wrong_lots = True
                for pack_lot in pack_lots:
                    lot_id, qty = pack_lot['lot_id'], pack_lot['qty']
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': lot_id,
                    })
                if not pack_lots and not float_is_zero(qty_done, precision_rounding=move.product_uom.rounding):
                    move.quantity_done = qty_done
        return has_wrong_lots

    @api.model
    def add_payment(self, data):
        """Create a new payment for the order"""
        if data['amount'] == 0.0:
            return
        return super(pos_order, self).add_payment(data)

    # @api.one
    def send_reserve_mail(self):
        if self and self.customer_email and self.reserved and self.fresh_order:
            try:
                template_id = self.env['ir.model.data'].get_object_reference('flexibite_com_advance',
                                                                             'email_template_pos_ereceipt')
                template_obj = self.env['mail.template'].browse(template_id[1])
                template_obj.send_mail(self.id, force_send=True, raise_exception=False)
            except Exception as e:
                _logger.error('Unable to send email for order %s', e)

    def create(self, values):
        order_id = super(pos_order, self).create(values)

        if values.get('delivery_type') or values.get('delivery_user_id') or values.get('delivery_address') or \
                values.get('delivery_date') or values.get('delivery_time'):
            delivery_notif = []
            pos_session_ids = self.env['pos.session'].search([('state', '=', 'opened')])
            for session in pos_session_ids:
                delivery_notif.append([(self._cr.dbname, 'pos.order.line', session.user_id.id),
                                       {'delivery_pos_order': order_id.read()}])

            self.env['bus.bus'].sendmany(delivery_notif)
        # if order_id.rounding != 0:
        #     if rounding_journal_id:
        #         order_id.add_payment({
        #             'amount': order_id.rounding * -1,
        #             'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        #             'payment_name': _('Rounding'),
        #             'journal': rounding_journal_id.id,
        #         })
        # if not order_id.user_id.pos_user_type == 'cashier':
        #     notifications = []
        #     users = self.env['res.users'].search([])
        #     for user in users:
        #         if user.sales_persons:
        #             for salesperson in user.sales_persons:
        #                 if salesperson.id == order_id.user_id.id:
        #                     session = self.env['pos.session'].search([('user_id', '=', user.id)], limit=1)
        #                     if session:
        #                         notifications.append(
        #                             [(self._cr.dbname, 'lock.data', user.id), {'new_pos_order': order_id.read()}])
        #                         self.env['bus.bus'].sendmany(notifications)
        return order_id

    def _calculate_amount_total_by_points(self, loyalty_config, points):
        return (float(points) * loyalty_config[0].get('to_amount')) / (loyalty_config[0].get('points') or 1)

    def get_point_from_category(self, categ_id):
        if categ_id.loyalty_point:
            return categ_id.loyalty_point
        elif categ_id.parent_id:
            self.get_point_from_category(categ_id.parent_id)
        return False

    def _calculate_loyalty_points_by_order(self, loyalty_config):
        if loyalty_config.point_calculation:
            earned_points = self.amount_total * loyalty_config.point_calculation / 100
            amount_total = (earned_points * loyalty_config.to_amount) / loyalty_config.points
            return {
                'points': earned_points,
                'amount_total': amount_total
            }
        return False

    # @api.multi
    def refund(self):
        res = super(pos_order, self).refund()
        LoyaltyPoints = self.env['loyalty.point']
        refund_order_id = self.browse(res.get('res_id'))
        if refund_order_id:
            LoyaltyPoints.create({
                'pos_order_id': refund_order_id.id,
                'partner_id': self.partner_id.id,
                'points': refund_order_id.total_loyalty_redeem_points,
                'amount_total': refund_order_id.total_loyalty_redeem_amount,

            })
            LoyaltyPoints.create({
                'pos_order_id': refund_order_id.id,
                'partner_id': self.partner_id.id,
                'points': refund_order_id.total_loyalty_earned_points * -1,
                'amount_total': refund_order_id.total_loyalty_earned_amount * -1,

            })
            refund_order_id.write({
                'total_loyalty_earned_points': refund_order_id.total_loyalty_earned_points * -1,
                'total_loyalty_earned_amount': refund_order_id.total_loyalty_earned_amount * -1,
                'total_loyalty_redeem_points': 0.00,
                'total_loyalty_redeem_amount': 0.00,
            })
        return res

    # POS Reorder start here

    @api.model
    def calculate_order(self, domain):
        all_order_ids = False
        if domain and domain.get('domain'):
            all_order_ids = self.search(domain.get('domain'))
        if all_order_ids:
            return all_order_ids.ids
        else:
            return []

    @api.model
    def ac_pos_search_read(self, domain):
        domain = domain.get('domain')
        search_vals = self.search_read(domain)
        user_id = self.env['res.users'].browse(self._uid)
        tz = False
        result = []
        if self._context and self._context.get('tz'):
            tz = timezone(self._context.get('tz'))
        elif user_id and user_id.tz:
            tz = timezone(user_id.tz)
        if tz:
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            for val in search_vals:
                if sign == '-':
                    val.update({
                        'date_order': (val.get('date_order') - timedelta(hours=hour_tz, minutes=min_tz)).strftime(
                            '%Y-%m-%d %H:%M:%S')
                    })
                elif sign == '+':
                    val.update({
                        'date_order': (val.get('date_order') + timedelta(hours=hour_tz, minutes=min_tz)).strftime(
                            '%Y-%m-%d %H:%M:%S')
                    })
                result.append(val)
            return result
        else:
            return search_vals

    # POS Reorder end here

    # @api.one
    def multi_picking(self):
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        StockWarehouse = self.env['stock.warehouse']
        address = self.partner_id.address_get(['delivery']) or {}
        picking_type = self.picking_type_id
        order_picking = Picking
        return_picking = Picking
        return_pick_type = self.picking_type_id.return_picking_type_id or self.picking_type_id
        message = _(
            "This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (
                      self.id, self.name)
        if self.partner_id:
            destination_id = self.partner_id.property_stock_customer.id
        else:
            if (not picking_type) or (
                    not picking_type.default_location_dest_id):
                customerloc, supplierloc = StockWarehouse._get_partner_locations()
                destination_id = customerloc.id
            else:
                destination_id = picking_type.default_location_dest_id.id
        lst_picking = []
        location_ids = list(set([line.location_id.id for line in self.lines]))
        for loc_id in location_ids:
            picking_vals = {
                'origin': self.name,
                'partner_id': address.get('delivery', False),
                'date_done': self.date_order,
                'picking_type_id': picking_type.id,
                'company_id': self.company_id.id,
                'move_type': 'direct',
                'note': self.note or "",
                'location_id': loc_id,
                'location_dest_id': destination_id,
            }
            pos_qty = any(
                [x.qty > 0 for x in self.lines if x.product_id.type in ['product', 'consu']])
            if pos_qty:
                order_picking = Picking.create(picking_vals.copy())
                order_picking.message_post(body=message)
            neg_qty = any(
                [x.qty < 0 for x in self.lines if x.product_id.type in ['product', 'consu']])
            if neg_qty:
                return_vals = picking_vals.copy()
                return_vals.update({
                    'location_id': destination_id,
                    'location_dest_id': loc_id,
                    'picking_type_id': return_pick_type.id
                })
                return_picking = Picking.create(return_vals)
                return_picking.message_post(body=message)
            for line in self.lines.filtered(
                    lambda l: l.product_id.type in [
                        'product',
                        'consu'] and l.location_id.id == loc_id and not float_is_zero(
                        l.qty,
                        precision_digits=l.product_id.uom_id.rounding)):
                Move.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
                    'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': loc_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else loc_id,
                })
            if return_picking:
                self.write({'picking_ids': [(4, return_picking.id)]})
                self._force_picking_done(return_picking)
            if order_picking:
                self.write({'picking_ids': [(4, order_picking.id)]})
                self._force_picking_done(order_picking)
        return True

    def create_picking(self):
        """Create a picking for each order and validate it."""
        # if self.order_status not in ['full', 'partial'] and not self.order_booked and not self.picking_id:
        #     super(pos_order, self).create_picking()
        # return True
        Picking = self.env['stock.picking']
        # If no email is set on the user, the picking creation and validation will fail be cause of
        # the 'Unable to log message, please configure the sender's email address.' error.
        # We disable the tracking in this case.
        if not self.env.user.partner_id.email:
            Picking = Picking.with_context(tracking_disable=True)
        Move = self.env['stock.move']
        StockWarehouse = self.env['stock.warehouse']
        for order in self:
            # custom multi location
            multi_loc = False
            for line_order in order.lines:
                if line_order.location_id:
                    multi_loc = True
                    break
            if multi_loc:
                order.multi_picking()
            else:
                if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                    continue
                address = order.partner_id.address_get(['delivery']) or {}
                picking_type = order.picking_type_id
                return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
                order_picking = Picking
                return_picking = Picking
                moves = Move
                if order and order.store_id and order.store_id.location_id:
                    location_id = order.store_id.location_id.id
                else:
                    location_id = picking_type.default_location_src_id.id
                if order.partner_id:
                    destination_id = order.partner_id.property_stock_customer.id
                else:
                    if (not picking_type) or (not picking_type.default_location_dest_id):
                        customerloc, supplierloc = StockWarehouse._get_partner_locations()
                        destination_id = customerloc.id
                    else:
                        destination_id = picking_type.default_location_dest_id.id

                if picking_type:
                    message = _(
                        "This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (
                                  order.id, order.name)
                    picking_vals = {
                        'origin': order.name,
                        'partner_id': address.get('delivery', False),
                        'user_id': False,
                        'date_done': order.date_order,
                        'picking_type_id': picking_type.id,
                        'company_id': order.company_id.id,
                        'move_type': 'direct',
                        'note': order.note or "",
                        'location_id': location_id,
                        'location_dest_id': destination_id,
                    }
                    pos_qty = any([x.qty > 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                    if pos_qty:
                        order_picking = Picking.create(picking_vals.copy())
                        if self.env.user.partner_id.email:
                            order_picking.message_post(body=message)
                        else:
                            order_picking.sudo().message_post(body=message)
                    neg_qty = any([x.qty < 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                    if neg_qty:
                        return_vals = picking_vals.copy()
                        return_vals.update({
                            'location_id': destination_id,
                            'location_dest_id': return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                            'picking_type_id': return_pick_type.id
                        })
                        return_picking = Picking.create(return_vals)
                        if self.env.user.partner_id.email:
                            return_picking.message_post(body=message)
                        else:
                            return_picking.message_post(body=message)

                for line in order.lines.filtered(
                        lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                                  precision_rounding=l.product_id.uom_id.rounding)):
                    moves |= Move.create({
                        'name': line.name,
                        'product_uom': line.uom_id.id if line.uom_id else line.product_id.uom_id.id,
                        'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
                        'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': abs(line.qty),
                        'state': 'draft',
                        'location_id': location_id if line.qty >= 0 else destination_id,
                        'location_dest_id': destination_id if line.qty >= 0 else return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                    })

                # prefer associating the regular order picking, not the return
                order.write({'picking_id': order_picking.id or return_picking.id})

                if return_picking:
                    order._force_picking_done(return_picking)
                if order_picking:
                    order._force_picking_done(order_picking)

                # when the pos.config has no picking_type_id set only the moves will be created
                if moves and not return_picking and not order_picking:
                    moves._action_assign()
                    moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()

        return True

    # @api.multi
    def do_internal_transfer(self):
        for order in self:
            if order.config_id.reserve_stock_location_id and order.config_id.stock_location_id:
                # Move Lines
                temp_move_lines = []
                for line in order.lines:
                    if line.product_id.default_code:
                        name = [line.product_id.default_code]
                    else:
                        name = line.product_id.name
                    if line.product_id.type != "service":
                        move_vals = (0, 0, {
                            'product_id': line.product_id.id,
                            'name': name,
                            'product_uom_qty': line.qty,
                            'quantity_done': line.qty,
                            'location_id': order.config_id.stock_location_id.id,
                            'location_dest_id': order.config_id.reserve_stock_location_id.id,
                            'product_uom': line.product_id.uom_id.id,
                        })
                        temp_move_lines.append(move_vals)
                warehouse_obj = self.env['stock.warehouse'].search([
                    ('lot_stock_id', '=', order.config_id.stock_location_id.id)], limit=1)
                if warehouse_obj:
                    picking_type_obj = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', warehouse_obj.id), ('code', '=', 'internal')])
                    if picking_type_obj and temp_move_lines:
                        picking_vals = {
                            'picking_type_id': picking_type_obj.id,
                            'location_id': order.config_id.stock_location_id.id,
                            'location_dest_id': order.config_id.reserve_stock_location_id.id,
                            'state': 'draft',
                            'move_lines': temp_move_lines,
                            'origin': order.name
                        }
                        picking_obj = self.env['stock.picking'].create(picking_vals)
                        if picking_obj and picking_obj.move_lines:
                            picking_obj.action_confirm()
                            for each in picking_obj.move_lines:
                                each.write({'quantity_done': each.product_uom_qty})
                            picking_obj.action_assign()
                            picking_obj.button_validate()
                            stock_transfer_id = self.env['stock.immediate.transfer'].search(
                                [('pick_ids', '=', picking_obj.id)], limit=1)
                            if stock_transfer_id:
                                stock_transfer_id.process()
                            order.picking_id = picking_obj.id

    # @api.multi
    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_due(self):
        for each in self:
            each.amount_due = (each.amount_total - each.amount_paid) + each.change_amount_for_wallet

    # @api.multi
    @api.depends('lines')
    def _find_order_status(self):
        for order in self:
            partial, full = [], []
            line_count = 0;
            line_partial = False
            for line in order.lines:
                if not line.cancel_item:
                    line_count += 1
                    if line.line_status == "partial":
                        order.order_status = "partial"
                        line_partial = True
                        break
                    if line.line_status == "full":
                        full.append(True)
            if len(full) == line_count:
                if not False in full and not line_partial:
                    order.order_status = "full"
            elif full:
                order.order_status = "partial"

    @api.model
    def graph_data(self, from_date, to_date, category, limit, session_id, current_session_report):
        if from_date and not to_date:
            if from_date.split(' ')[0] and len(from_date.split(' ')) > 1:
                to_date = from_date.split(' ')[0] + " 23:59:59"
        elif to_date and not from_date:
            if to_date.split(' ')[0] and len(to_date.split(' ')) > 1:
                from_date = to_date.split(' ')[0] + " 00:00:00"

        if limit == "ALL":
            limit = 10
        try:
            if from_date and to_date:
                if category == 'top_customer':
                    if current_session_report:
                        order_ids = self.env['pos.order'].search([('partner_id', '!=', False),
                                                                  ('date_order',
                                                                   '>=', from_date),
                                                                  ('date_order',
                                                                   '<=', to_date),
                                                                  ('session_id', '=', session_id)],
                                                                 order='date_order desc')
                    else:
                        order_ids = self.env['pos.order'].search([('partner_id', '!=', False),
                                                                  ('date_order',
                                                                   '>=', from_date),
                                                                  ('date_order', '<=', to_date)],
                                                                 order='date_order desc')
                    result = []
                    record = {}
                    if order_ids:
                        for each_order in order_ids:
                            if each_order.partner_id in record:
                                record.update({each_order.partner_id: record.get(
                                    each_order.partner_id) + each_order.amount_total})
                            else:
                                record.update(
                                    {each_order.partner_id: each_order.amount_total})
                    if record:
                        result = [(k.name, v) for k, v in record.items()]
                        result = sorted(
                            result, key=lambda x: x[1], reverse=True)
                    if limit == 'ALL':
                        return result
                    return result[:int(limit)]
                if category == 'top_products':
                    condition_statement = """
                                WHERE 
                                    po.date_order > '{0}' 
                                AND 
                                    po.date_order <= '{1}'
                            """.format(from_date, to_date)
                    if current_session_report:
                        condition_statement += """
                                AND 
                                    po.session_id = '{0}'""".format(session_id)
                    self._cr.execute("""
                                SELECT 
                                    pt.name, sum(psl.qty) 
                                FROM 
                                    pos_order_line AS psl
                                LEFT JOIN 
                                    pos_order AS po ON (po.id = psl.order_id)
                                LEFT JOIN 
                                    product_product AS pp ON (psl.product_id = pp.id)
                                LEFT JOIN 
                                    product_template AS pt ON (pt.id = pp.product_tmpl_id)
                                %s
                                GROUP BY pt.name
                                ORDER BY sum(psl.qty) DESC limit %s;
                                """ % (condition_statement, limit))
                    result = self._cr.fetchall()
                    return result
                if category == 'cashiers':
                    if current_session_report:
                        self._cr.execute("""
                                    SELECT 
                                        ps.name,
                                        sum(pp.amount)
                                    FROM 
                                        pos_payment pp,
                                        (SELECT 
                                            pc.name 
                                        FROM 
                                            pos_session AS pos 
                                        LEFT JOIN 
                                            pos_config as pc on pos.config_id = pc.id 
                                        WHERE 
                                            pos.id='{0}') as ps
                                    WHERE 
                                        pp.session_id = '{0}'
                                    GROUP BY 
                                        ps.name;
                                    """.format(session_id)
                                         )
                        find_session = self._cr.fetchall()
                        return find_session
                    else:
                        self._cr.execute("""
                                    SELECT 
                                        ps.name,
                                        sum(pp.amount)
                                    FROM 
                                        pos_payment pp,
                                        (SELECT 
                                            pc.name 
                                        FROM 
                                            pos_session AS pos 
                                        LEFT JOIN 
                                            pos_config as pc on pos.config_id = pc.id 
                                        ) as ps
                                    GROUP BY 
                                        ps.name;
                                    """)
                        find_session = self._cr.fetchall()
                        return find_session
                if category == 'sales_by_location':
                    if current_session_report:
                        self._cr.execute("""
                                        SELECT (loc1.name || '/' || loc.name) as name, sum(psl.price_unit) FROM pos_order_line AS psl
                                        JOIN pos_order AS po ON (po.id = psl.order_id)
                                        JOIN stock_location AS loc ON (loc.id = po.location_id)
                                        JOIN stock_location AS loc1 ON (loc.location_id = loc1.id)
                                        WHERE po.date_order AT TIME ZONE 'GMT' >= '%s'
                                        AND po.date_order AT TIME ZONE 'GMT' <= '%s'
                                        AND po.session_id = '%s'
                                        GROUP BY loc.name, loc1.name
                                        limit %s
                                    """ % ((from_date, to_date, session_id, limit)))
                        return self._cr.fetchall()
                    else:
                        self._cr.execute("""
                                    SELECT (loc1.name || '/' || loc.name) as name, sum(psl.price_unit) FROM pos_order_line AS psl
                                    JOIN pos_order AS po ON (po.id = psl.order_id)
                                    JOIN stock_location AS loc ON (loc.id = po.location_id)
                                    JOIN stock_location AS loc1 ON (loc.location_id = loc1.id)
                                    WHERE po.date_order AT TIME ZONE 'GMT' >= '%s'
                                    AND po.date_order AT TIME ZONE 'GMT' <= '%s'
                                    GROUP BY loc.name, loc1.name
                                    limit %s
                                    """ % ((from_date, to_date, limit)))
                        return self._cr.fetchall()
                if category == 'income_by_journals':
                    if current_session_report:
                        self._cr.execute("""
                                    select  pm.name,round(sum(amount),2) from pos_payment as pp
                                    join pos_payment_method as pm on pm.id = pp.payment_method_id
                                    where pp.create_date AT TIME ZONE 'GMT' >= '%s' and pp.create_date AT TIME ZONE 'GMT' <= '%s' and pp.session_id = '%s'
                                    group by pm.name
                                    limit %s
                                """ % ((from_date, to_date, session_id, limit)))
                        return self._cr.fetchall()
                    else:
                        self._cr.execute("""
                                    select  pm.name,round(sum(amount),2) from pos_payment as pp
                                    join pos_payment_method as pm on pm.id = pp.payment_method_id
                                    where pp.create_date AT TIME ZONE 'GMT' >= '%s' and pp.create_date AT TIME ZONE 'GMT' <= '%s' 
                                    group by pm.name
                                    limit %s
                                """ % ((from_date, to_date, limit)))
                        return self._cr.fetchall()
                if category == 'top_category':
                    condition_statement = """
                                                    WHERE 
                                                        po.date_order > '{0}' 
                                                    AND 
                                                        po.date_order <= '{1}'
                                                """.format(from_date, to_date)
                    if current_session_report:
                        condition_statement += """
                                                    AND 
                                                        po.session_id = '{0}'""".format(session_id)
                    self._cr.execute("""
                                SELECT
                                    pc.name, 
                                    sum((pol.price_unit * pol.qty) - pol.discount) 
                                FROM
                                    pos_order_line AS pol
                                LEFT JOIN 
                                    pos_order po ON (po.id = pol.order_id)
                                LEFT JOIN 
                                    product_product pp ON (pol.product_id = pp.id)
                                LEFT JOIN 
                                    product_template pt ON (pol.product_id = pt.id)
                                LEFT JOIN 
                                    pos_category pc ON (pc.id=pt.pos_categ_id)
                                %s
                                GROUP BY 
                                    pc.name
                                ORDER BY 
                                    sum((pol.price_unit * pol.qty) - pol.discount)  DESC
                                limit %s""" % (condition_statement, limit))
                    result = self._cr.fetchall()
                    return result
                if category == 'pos_benifit':
                    domain = False
                    if current_session_report:
                        domain = [('date_order', '>=', from_date),
                                  ('date_order', '<=', to_date),
                                  ('session_id', '=', session_id)]
                    else:
                        domain = [('date_order', '>=', from_date),
                                  ('date_order', '<=', to_date)]
                    if domain and len(domain) > 1:
                        order_ids = self.env['pos.order'].search(
                            domain, order='date_order desc')
                        if len(order_ids) > 0:
                            profit_amount = 0
                            loss_amount = 0
                            loss = 0
                            profit = 0
                            for order in order_ids:
                                for line in order.lines:
                                    cost_price = line.product_id.standard_price * line.qty
                                    sale_price = line.price_subtotal_incl
                                    profit_amount += (sale_price - cost_price)
                                    loss_amount += (cost_price - sale_price)
                            if loss_amount > 0:
                                loss = loss_amount
                            if profit_amount > 0:
                                profit = profit_amount
                            return [('Profit', profit), ('Loss', loss)]
                    return False
        except Exception as e:
            return {'error': e}

    @api.model
    def payment_summary_report(self, vals):
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(vals.get('start_date'), vals.get('end_date'), current_time_zone)
        final_data_dict = dict.fromkeys(['journal_details', 'salesmen_details', 'summary_data'], {})
        sql = False

        if vals.get('summary') == 'journals':
            sql = """ SELECT
                            REPLACE(CONCAT(to_char(to_timestamp(
                            EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'),'Month'),
                            '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                            ' ', '') AS month,
                            ppm.name, ppm.id,
                            SUM(pp.amount) AS amount
                            FROM pos_payment AS pp
                            INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                            WHERE payment_date BETWEEN  '%s' AND '%s'
                            GROUP BY month, ppm.name, ppm.id
                            ORDER BY month ASC
                        """ % (current_time_zone, current_time_zone, s_date, e_date)

        if vals.get('summary') == 'sales_person':
            sql = """ SELECT
                            REPLACE(CONCAT(to_char(to_timestamp(
                            EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'), 'Month'), 
                            '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                            ' ', '') AS month,
                            rp.name AS login, ppm.name, SUM(pp.amount) AS amount
                            FROM
                            pos_order AS po
                            INNER JOIN res_users AS ru ON ru.id = po.user_id
                            INNER JOIN res_partner AS rp ON rp.id = ru.partner_id
                            INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
                            INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                            WHERE
                            po.date_order BETWEEN '%s' AND '%s'
                            GROUP BY ppm.name, rp.name, month""" % (
                current_time_zone, current_time_zone, s_date, e_date)
        self._cr.execute(sql)
        sql_result = self._cr.dictfetchall()

        if sql_result:
            result = self.prepare_payment_summary_data(sql_result, vals.get('summary'))
            if vals.get('summary') == 'journals':
                final_data_dict.update({'journal_details': result[0], 'summary_data': result[1]})
                return final_data_dict
            else:
                final_data_dict.update({'salesmen_details': result[0]})
                return final_data_dict
        else:
            return final_data_dict

    @api.model
    def prepare_payment_summary_data(self, row_data, key):
        payment_details = {}
        summary_data = {}

        for each in row_data:
            if key == 'journals':
                payment_details.setdefault(each['month'], {})
                payment_details[each['month']].update({each['name']: each['amount']})
                summary_data.setdefault(each['name'], 0.0)
                summary_data.update({each['name']: summary_data[each['name']] + each['amount']})
            else:
                payment_details.setdefault(each['login'], {})
                payment_details[each['login']].setdefault(each['month'], {each['name']: 0})
                payment_details[each['login']][each['month']].update({each['name']: each['amount']})

        return [payment_details, summary_data]

    @api.model
    def product_summary_report(self, vals):
        product_summary_dict = {}
        category_summary_dict = {}
        payment_summary_dict = {}
        location_summary_dict = {}
        if vals:
            product_qty = 0
            location_qty = 0
            category_qty = 0
            payment = 0
            order_detail = self.env['pos.order'].search([('date_order', '>=', vals.get('start_date')),
                                                         ('date_order', '<=', vals.get('end_date'))
                                                         ])
            if ('product_summary' in vals.get('summary') or len(vals.get('summary')) == 0):
                if order_detail:
                    for each_order in order_detail:
                        for each_order_line in each_order.lines:
                            product_summary_dict.setdefault(
                                each_order_line.product_id.id, [each_order_line.product_id.display_name, 0.0])
                            product_summary_dict[each_order_line.product_id.id] = [
                                each_order_line.product_id.display_name,
                                each_order_line.qty + product_summary_dict[each_order_line.product_id.id][1]]
            if ('category_summary' in vals.get('summary') or len(vals.get('summary')) == 0):
                d1 = {}
                if order_detail:
                    for each_order in order_detail:
                        for each_order_line in each_order.lines:
                            if each_order_line.product_id.pos_categ_id.name in category_summary_dict:
                                category_qty = category_summary_dict[each_order_line.product_id.pos_categ_id.name]
                                category_qty += each_order_line.qty
                            else:
                                category_qty = each_order_line.qty
                            category_summary_dict[each_order_line.product_id.pos_categ_id.name] = category_qty
                    if (False in category_summary_dict):
                        category_summary_dict['Others'] = category_summary_dict.pop(False)

            if ('payment_summary' in vals.get('summary') or len(vals.get('summary')) == 0):
                if order_detail:
                    for each_order in order_detail:
                        for payment_line in each_order.payment_ids:
                            if payment_line.payment_method_id.name in payment_summary_dict:
                                payment = payment_summary_dict[payment_line.payment_method_id.name]
                                payment += payment_line.amount
                            else:
                                payment = payment_line.amount
                            payment_summary_dict[payment_line.payment_method_id.name] = float(format(payment, '2f'))

            if ('location_summary' in vals.get('summary') or len(vals.get('summary')) == 0):
                location_list = []
                for each_order in order_detail:
                    location_summary_dict[each_order.picking_id.location_id.name] = {}
                for each_order in order_detail:
                    for each_order_line in each_order.lines:
                        if each_order_line.product_id.name in location_summary_dict[
                            each_order.picking_id.location_id.name]:
                            location_qty = location_summary_dict[each_order.picking_id.location_id.name][
                                each_order_line.product_id.name]
                            location_qty += each_order_line.qty
                        else:
                            location_qty = each_order_line.qty
                        location_summary_dict[each_order.picking_id.location_id.name][
                            each_order_line.product_id.name] = location_qty
                location_list.append(location_summary_dict)

        return {
            'product_summary': product_summary_dict,
            'category_summary': category_summary_dict,
            'payment_summary': payment_summary_dict,
            'location_summary': location_summary_dict,
        }

    def _is_pos_order_paid(self):
        if self.config_id.enable_wallet:
            return float_is_zero(0, precision_rounding=self.currency_id.rounding)
        return super(pos_order, self)._is_pos_order_paid()

    def _get_amount_receivable(self):
        if self.config_id.enable_wallet:
            return self.amount_paid
        return super(pos_order, self)._get_amount_receivable()

    @api.model
    def order_summary_report(self, vals):
        order_list = {}
        order_list_sorted = []
        category_list = {}
        payment_list = {}
        if vals:
            if (vals['state'] == ''):
                if ('order_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date'))])
                    for each_order in orders:
                        order_list[each_order.state] = []
                    for each_order in orders:
                        if each_order.state in order_list:
                            order_list[each_order.state].append({
                                'order_ref': each_order.name,
                                'order_date': each_order.date_order,
                                'total': float(format(each_order.amount_total, '.2f'))
                            })
                        else:
                            order_list.update({
                                each_order.state.append({
                                    'order_ref': each_order.name,
                                    'order_date': each_order.date_order,
                                    'total': float(format(each_order.amount_total, '.2f'))
                                })
                            })
                if ('category_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    count = 0.00
                    amount = 0.00
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date'))])
                    for each_order in orders:
                        category_list[each_order.state] = {}
                    for each_order in orders:
                        for order_line in each_order.lines:
                            if each_order.state == 'paid':
                                if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                    count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                    amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                    count += order_line.qty
                                    amount += order_line.price_subtotal_incl
                                else:
                                    count = order_line.qty
                                    amount = order_line.price_subtotal_incl
                            if each_order.state == 'done':
                                if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                    count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                    amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                    count += order_line.qty
                                    amount += order_line.price_subtotal_incl
                                else:
                                    count = order_line.qty
                                    amount = order_line.price_subtotal_incl
                            if each_order.state == 'invoiced':
                                if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                    count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                    amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                    count += order_line.qty
                                    amount += order_line.price_subtotal_incl
                                else:
                                    count = order_line.qty
                                    amount = order_line.price_subtotal_incl
                            category_list[each_order.state].update(
                                {order_line.product_id.pos_categ_id.name: [count, amount]})
                        if (False in category_list[each_order.state]):
                            category_list[each_order.state]['others'] = category_list[each_order.state].pop(False)

                if ('payment_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    count = 0
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date'))])
                    for each_order in orders:
                        payment_list[each_order.state] = {}
                    for each_order in orders:
                        for payment_line in each_order.payment_ids:
                            if each_order.state == 'paid':
                                if payment_line.payment_method_id.name in payment_list[each_order.state]:
                                    count = payment_list[each_order.state][payment_line.payment_method_id.name]
                                    count += payment_line.amount
                                else:
                                    count = payment_line.amount
                            if each_order.state == 'done':
                                if payment_line.payment_method_id.name in payment_list[each_order.state]:
                                    count = payment_list[each_order.state][payment_line.payment_method_id.name]
                                    count += payment_line.amount
                                else:
                                    count = payment_line.amount
                            if each_order.state == 'invoiced':
                                if payment_line.payment_method_id.name in payment_list[each_order.state]:
                                    count = payment_list[each_order.state][payment_line.payment_method_id.name]
                                    count += payment_line.amount
                                else:
                                    count = payment_line.amount
                            payment_list[each_order.state].update(
                                {payment_line.payment_method_id.name: float(format(count, '.2f'))})
                return {'order_report': order_list, 'category_report': category_list, 'payment_report': payment_list,
                        'state': vals['state']}
            else:
                order_list = []
                if ('order_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date')),
                         ('state', '=', vals.get('state'))])
                    for each_order in orders:
                        order_list.append({
                            'order_ref': each_order.name,
                            'order_date': each_order.date_order,
                            'total': float(format(each_order.amount_total, '.2f'))
                        })
                    order_list_sorted = sorted(order_list, key=itemgetter('order_ref'))

                if ('category_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    count = 0.00
                    amount = 0.00
                    values = []
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date')),
                         ('state', '=', vals.get('state'))])
                    for each_order in orders:
                        for order_line in each_order.lines:
                            if order_line.product_id.pos_categ_id.name in category_list:
                                count = category_list[order_line.product_id.pos_categ_id.name][0]
                                amount = category_list[order_line.product_id.pos_categ_id.name][1]
                                count += order_line.qty
                                amount += order_line.price_subtotal_incl
                            else:
                                count = order_line.qty
                                amount = order_line.price_subtotal_incl
                            category_list.update({order_line.product_id.pos_categ_id.name: [count, amount]})
                    if (False in category_list):
                        category_list['others'] = category_list.pop(False)
                if ('payment_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                    count = 0
                    orders = self.search(
                        [('date_order', '>=', vals.get('start_date')), ('date_order', '<=', vals.get('end_date')),
                         ('state', '=', vals.get('state'))])
                    for each_order in orders:
                        for payment_line in each_order.payment_ids:
                            if payment_line.payment_method_id.name in payment_list:
                                count = payment_list[payment_line.payment_method_id.name]
                                count += payment_line.amount
                            else:
                                count = payment_line.amount
                            payment_list.update({payment_line.payment_method_id.name: float(format(count, '.2f'))})
            return {
                'order_report': order_list_sorted,
                'category_report': category_list,
                'payment_report': payment_list,
                'state': vals['state']
            }

    increment_number = fields.Char(string="Increment Number")
    customer_email = fields.Char('Customer Email')
    order_make_picking = fields.Boolean(string='Deliver')
    is_debit = fields.Boolean(string="Is Debit")
    parent_return_order = fields.Char('Return Order ID', size=64)
    return_seq = fields.Integer('Return Sequence')
    return_process = fields.Boolean('Return Process')
    back_order = fields.Char('Back Order', size=256, default=False, copy=False)
    # is_rounding = fields.Boolean("Is Rounding")
    # rounding_option = fields.Char("Rounding Option")
    # rounding = fields.Float(string='Rounding', digits=0)
    delivery_date = fields.Char("Delivery Date")
    delivery_time = fields.Char("Delivery Time")
    delivery_address = fields.Char("Delivery Address")
    delivery_charge_amt = fields.Float("Delivery Charge")
    total_loyalty_earned_points = fields.Float("Earned Loyalty Points")
    total_loyalty_earned_amount = fields.Float("Earned Loyalty Amount")
    total_loyalty_redeem_points = fields.Float("Redeemed Loyalty Points")
    total_loyalty_redeem_amount = fields.Float("Redeemed Loyalty Amount")
    change_amount_for_wallet = fields.Float('Wallet Amount')  # store wallet amount
    picking_ids = fields.Many2many(
        "stock.picking",
        string="Multiple Picking",
        copy=False)
    reserved = fields.Boolean("Reserved", readonly=True)
    partial_pay = fields.Boolean("Partial Pay", readonly=True)
    order_booked = fields.Boolean("Booked", readonly=True)
    unreserved = fields.Boolean("Unreserved")
    amount_due = fields.Float(string='Amount Due', compute='_compute_amount_due')
    reserve_delivery_date = fields.Date(string="Reserve Delivery Date")
    cancel_order = fields.Char('Cancel Order')
    order_status = fields.Selection([('full', 'Fully Cancelled'), ('partial', 'Partially Cancelled')],
                                    'Order Status')  # compute="_find_order_status"
    fresh_order = fields.Boolean("Fresh Order")
    table_ids = fields.Many2many('restaurant.table', string="Tables", help='The table where this order was served')
    store_id = fields.Many2one("pos.store", string="Shop")
    rating = fields.Selection(
        [('0', 'Bad'), ('1', 'Not bad'), ('2', 'Normal'), ('3', 'Good'), ('4', 'Very Good'), ('5', 'Excellent')],
        'Rating')
    salesman_id = fields.Many2one('res.users', string='Salesman')
    delivery_type = fields.Selection([('none', 'None'), ('pending', 'Pending'), ('delivered', 'Delivered')],
                                     string="Delivery Type", default="none")
    delivery_user_id = fields.Many2one('res.users', string="Delivery User")
    order_on_debit = fields.Boolean(string='Ordered On Debit')
    pos_normal_receipt_html = fields.Char(string="Pos Normal Receipt")
    pos_xml_receipt_html = fields.Char(string="Pos XML Receipt")


class pos_order_line(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def update_orderline_state(self, vals):
        order_line = self.browse(vals['order_line_id'])
        res = order_line.sudo().write({
            'state': vals['state']
        })
        vals['pos_reference'] = order_line.order_id.pos_reference
        # vals['pos_cid'] = order_line.pos_cid
        notifications = []
        notifications.append(
            ((self._cr.dbname, 'pos.order.line', order_line.create_uid.id), {'order_line_state': vals}))
        self.env['bus.bus'].sendmany(notifications)
        return res

    @api.model
    def update_all_orderline_state(self, vals):
        notifications = []
        if vals:
            for val in vals:
                state = False
                if val.get('route'):
                    if val.get('state') == 'waiting':
                        state = 'preparing'
                    elif val.get('state') == 'preparing':
                        state = 'delivering'
                    elif val.get('state') == 'delivering':
                        state = 'done'
                    elif val.get('state') == 'cancel':
                        state = 'cancel'
                else:
                    if val.get('state') == 'waiting':
                        state = 'delivering'
                    elif val.get('state') == 'delivering':
                        state = 'done'
                    elif val.get('state') == 'cancel':
                        state = 'cancel'
                if state:
                    order_line = self.browse(val['order_line_id'])
                    order_line.sudo().write({'state': state})
                    val['pos_reference'] = order_line.order_id.pos_reference
                    val['pos_cid'] = order_line.pos_cid
                    val['state'] = state
                    notifications.append(
                        [(self._cr.dbname, 'pos.order.line', order_line.create_uid.id), {'order_line_state': val}])
            if len(notifications) > 0:
                self.env['bus.bus'].sendmany(notifications)
        return True

    # @api.model
    # def create_mo(self, list):
    #     """
    #     Create manufacturing order for order which has item to be cook
    #     :return type : True  or False
    #     """
    #     flag = True
    #     if self and self.product_id and self.product_id.product_tmpl_id.id and self.qty > 0:
    #         bom_obj = self.env['mrp.bom']
    #         bom_id = bom_obj._bom_find(self.product_id.product_tmpl_id, self.product_id)
    #         if bom_id:
    #             mrp_production = self.env['mrp.production']
    #             default_dict = mrp_production.default_get(['priority', 'date_planned_start', 'product_uom',
    #                                                        'product_uos_qty', 'user_id', 'company_id',
    #                                                        'name', 'date_planned', 'location_src_id',
    #                                                        'location_dest_id', 'message_follower_ids'])
    #             default_dict.update({
    #                 'product_id': self.product_id.id,
    #                 'bom_id': bom_id.id or False,
    #                 'product_qty': self.qty,
    #                 'product_uom_id': self.product_id.uom_id.id,
    #                 'origin': 'Kitchen POS',
    #                 'product_uom_qty': self.qty,
    #                 # 'product_uos': self.product_id.uom_id.id,
    #                 'company_id': self.order_id.company_id.id,
    #                 # 'location_src_id': self.order_id.session_id.config_id.stock_location_id.id,
    #                 # 'location_dest_id': self.order_id.session_id.config_id.stock_location_id.id,
    #             })

    #             if self.order_id.session_id.config_id.mrp_operation_type:
    #                 default_dict.update({
    #                     'picking_type_id': self.order_id.session_id.config_id.mrp_operation_type.id,
    #                 })

    #             mo_id = mrp_production.create(default_dict)
    #             mo_id.write({'line_ref': self.line_ref, 'pos_order_id': self.order_id.id})
    #             list_data = []
    #             if list:
    #                 for data in list:
    #                     for line in mo_id.move_raw_ids:
    #                         if line.product_id.id == data.product_id.id:
    #                             list_data.append(data.id)
    #             mo_id.write({'pos_bom_line_ids': [[6, 0, list_data]]})

    #             # for each in bom_id.bom_line_ids:
    #             #     product_available_qty = self.env['product.product'].browse(each.product_id.id).with_context(
    #             #         {'location': self.order_id.session_id.config_id.stock_location_id.id}).qty_available
    #             #     if product_available_qty < each.product_qty:
    #             #         flag = False
    #             if flag:
    #                 mo_id.action_assign()
    #                 mo_id.open_produce_product()
    #             self.write({'mo_id': mo_id.id})
    #     return True

    def create_mo(self, list):
        """
        Create manufacturing order for order which has item to be cook
        :return type : True  or False
        """
        if self and self.product_id and self.product_id.product_tmpl_id.id and self.qty > 0:
            bom_obj = self.env['mrp.bom']
            bom_id = bom_obj._bom_find(self.product_id.product_tmpl_id, self.product_id)
            if bom_id:
                mrp_production = self.env['mrp.production']
                default_dict = mrp_production.default_get(
                    ['priority', 'date_planned_start', 'product_uom',
                     'product_uom_qty', 'user_id', 'company_id',
                     'name', 'date_planned', 'location_src_id',
                     'location_dest_id', 'message_follower_ids'])
                default_dict.update({
                    'product_id': self.product_id.id,
                    'bom_id': bom_id.id or False,
                    'product_qty': self.qty,
                    'product_uom_id': self.product_id.uom_id.id,
                    'origin': 'Kitchen POS',
                    'product_uom_qty': self.qty,
                    # 'product_uos': self.product_id.uom_id.id,
                    'company_id': self.order_id.company_id.id,
                    # 'location_src_id': self.order_id.session_id.config_id.stock_location_id.id,
                    # 'location_dest_id': self.order_id.session_id.config_id.stock_location_id.id,
                })

                if self.order_id.session_id.config_id.mrp_operation_type:
                    default_dict.update({
                        'picking_type_id': self.order_id.session_id.config_id.mrp_operation_type.id,
                    })
                mo_id = mrp_production.create(default_dict)
                mo_id.write({'line_ref': self.line_ref, 'pos_order_id': self.order_id.id})
                list_data = []
                if list:
                    for data in list:
                        for line in mo_id.move_raw_ids:
                            if line.product_id.id == data.product_id.id:
                                list_data.append(data.id)
                mo_id.write({'pos_bom_line_ids': [[6, 0, list_data]]})
                mo_id.action_assign()
                mo_id.open_produce_product()
                self.write({'mo_id': mo_id.id})
        return True

    @api.model
    def create(self, values):
        mo_id = False
        if values.get('line_ref'):
            mo_id = self.env['mrp.production'].sudo().search([('line_ref', '=', str(values.get('line_ref')))])

        try:
            if values.get('uom_id'):
                values['uom_id'] = values.get('uom_id')[0]
        except Exception:
            values['uom_id'] = None
            pass
        if values.get('product_id'):
            #             if self.env['pos.order'].browse(values['order_id']).session_id.config_id.prod_for_payment.id == values.get('product_id'):
            #                 return
            if self.env['pos.order'].browse(
                    values['order_id']).session_id.config_id.refund_amount_product_id.id == values.get('product_id'):
                return
        if values.get('cancel_item_id'):
            line_id = self.browse(values.get('cancel_item_id'))
            if line_id and values.get('new_line_status'):
                values.update({'line_status': values.get('new_line_status')})
        bom_data = values.get('bom_lines');
        del values['bom_lines']
        res = super(pos_order_line, self).create(values)
        values['bom_lines'] = bom_data
        bom_order_line_list = []
        if values.get('bom_lines'):
            produce_product_qty = values.get('qty') or 1
            bom_order_line = self.env['pos.orderline.bom.line']
            for bom_line in values.get('bom_lines'):
                if bom_line.get('bom_selected'):
                    id = bom_order_line.create({
                        'prod_bom_id': bom_line.get('bom_id'),
                        'pos_order_line_id': res.id,
                        'bom_line_id': bom_line.get('bom_line_id'),
                        'qty': int(bom_line.get('bom_line_qty')) * int(produce_product_qty),
                        'product_id': bom_line.get('bom_line_product_id'),
                    })
                    bom_order_line_list.append(id)
                else:
                    id = bom_order_line.create({
                        'prod_bom_id': bom_line.get('bom_id'),
                        'pos_order_line_id': res.id,
                        'bom_line_id': bom_line.get('bom_line_id'),
                        'qty': 0.00,
                        'product_id': bom_line.get('bom_line_product_id'),
                    })
                    bom_order_line_list.append(id)
        if not mo_id:
            if res.order_id.session_id.config_id.generate_mo_after_payment:
                if res.order_id.amount_due <= 0:
                    res.create_mo(bom_order_line_list)
            else:
                res.create_mo(bom_order_line_list)
        else:
            if res.qty > mo_id.product_qty:
                id = self.env['change.production.qty'].create({'product_qty': res.qty, 'mo_id': mo_id.id})
                id.change_prod_qty()
            list_data = []
            if bom_order_line_list:
                for data in bom_order_line_list:
                    for line in mo_id.move_raw_ids:
                        if line.product_id.id == data.product_id.id:
                            list_data.append(data.id)
            # self._cr.execute("DELETE FROM pos_orderline_bom_line where id in (%s) " % ','.join(
            #     map(str, mo_id.pos_bom_line_ids.ids)))

            mo_id.write({'pos_bom_line_ids': [[6, 0, list_data]]})
            res.mo_id = mo_id.id
        return res

    @api.model
    def load_return_order_lines(self, pos_order_id):
        valid_return_lines = []
        current_date = datetime.today().strftime('%Y-%m-%d')
        if pos_order_id:
            order_id = self.env['pos.order'].browse(pos_order_id)
            if order_id and order_id.config_id.enable_print_valid_days:
                order_lines = self.search([('order_id', '=', pos_order_id), ('return_qty', '>', 0)])
                if order_lines:
                    for line in order_lines:
                        if line.return_valid_days > 0 and not line.product_id.is_dummy_product:
                            date_N_days_after = (
                                (order_id.date_order + timedelta(days=line.return_valid_days))).strftime('%Y-%m-%d')
                            if current_date <= date_N_days_after:
                                valid_return_lines.append(line.read()[0])
            else:
                return self.search_read([('order_id', '=', pos_order_id), ('return_qty', '>', 0)])
        return valid_return_lines

    cancel_item = fields.Boolean("Cancel Item")
    cost_price = fields.Float("Cost")
    line_status = fields.Selection(
        [('nothing', 'Nothing'), ('full', 'Fully Cancelled'), ('partial', 'Partially Cancelled')],
        'Order Status', default="nothing")
    line_note = fields.Char('Comment', size=512)
    deliver = fields.Boolean("Is deliver")
    return_qty = fields.Integer('Return QTY', size=64)
    return_process = fields.Char('Return Process')
    back_order = fields.Char('Back Order', size=256, default=False, copy=False)
    location_id = fields.Many2one('stock.location', string='Location')
    serial_nums = fields.Char("Serials")
    return_valid_days = fields.Integer(string="Return Valid Days")
    uom_id = fields.Many2one('uom.uom', string="UOM")
    mo_id = fields.Many2one('mrp.production', 'MO', invisible=True)
    line_ref = fields.Char("Mo ref")
    bom_lines = fields.One2many('pos.orderline.bom.line', 'pos_order_line_id', 'Bill of material')
    combo_ext_line_info = fields.Char("Com ref")
    tech_combo_data = fields.Char("Com ref")
    state = fields.Selection(
        selection=[("waiting", "Waiting"), ("preparing", "Preparing"), ("delivering", "Waiting/deliver"),
                   ("done", "Done"), ("cancel", "Cancel")], default="waiting")
    priority = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], string="Priority")
    is_main_combo_product = fields.Boolean("Is Main Combo Product")
    # mod_lines = fields.One2many('modifier.order.line', 'line_id', 'Modifiers')


class quick_cash_payment(models.Model):
    _name = "quick.cash.payment"
    _description = 'Used to Store Quick Cash Payment Button.'

    name = fields.Float(string='Amount')

    _sql_constraints = [
        ('quick_cash_payment', 'unique(name)', 'This amount already selected'),
    ]


class pos_session(models.Model):
    _inherit = 'pos.session'

    current_cashier_id = fields.Many2one('res.users', string="Cashier", readonly=True)
    locked = fields.Boolean("Locked")
    locked_by_user_id = fields.Many2one('res.users', string="Locked By")

    cashcontrol_ids = fields.One2many(comodel_name="custom.cashcontrol", inverse_name="pos_session_id",
                                      string="Cash Control Information")
    opening_balance = fields.Boolean(string="Opening Balance")
    store_id = fields.Many2one('pos.store', string='Store', related='user_id.default_store_id')
    increment_number = fields.Integer(string="Increment Number", default=0, size=3,
                                      help="This is a field is used for show increment number on kitchen screen when create pos order from point of sale.")

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        gift_card_vals = []
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        for order in self.order_ids:
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            for payment in order.payment_ids:
                amount, date = payment.amount, payment.payment_date
                if payment.payment_method_id.split_transactions:
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment],
                                                                               {'amount': amount}, date)
                    else:
                        split_receivables[payment] = self._update_amounts(split_receivables[payment],
                                                                          {'amount': amount}, date)
                else:
                    key = payment.payment_method_id
                    if payment.payment_method_id.is_cash_count:
                        combine_receivables_cash[key] = self._update_amounts(combine_receivables_cash[key],
                                                                             {'amount': amount}, date)
                    else:
                        combine_receivables[key] = self._update_amounts(combine_receivables[key], {'amount': amount},
                                                                        date)

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id.property_account_receivable_id.id
                invoice_receivables[key] = self._update_amounts(invoice_receivables[key],
                                                                {'amount': order._get_amount_receivable()},
                                                                order.date_order)
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(
                        lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            else:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    if self.config_id.enable_gift_card and \
                            (order_line.product_id.id == self.config_id.gift_card_product_id.id):
                        amount = order_line.price_subtotal_incl
                        amount_converted = self.company_id.currency_id.round(order_line.price_subtotal_incl)
                        gift_card_vals.append(
                            self._get_gift_card_credit_vals(amount, amount_converted, order_line.order_id))
                    else:
                        line = self._prepare_line(order_line)
                        # Combine sales/refund lines
                        sale_key = (
                            # account
                            line['income_account_id'],
                            # sign
                            -1 if line['amount'] < 0 else 1,
                            # for taxes
                            tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in
                                  line['taxes']),
                            line['base_tags'],
                        )
                        sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']},
                                                               line['date_order'])
                        # Combine tax lines
                        for tax in line['taxes']:
                            tax_key = (
                                tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                            order_taxes[tax_key] = self._update_amounts(
                                order_taxes[tax_key],
                                {'amount': tax['amount'], 'base_amount': tax['base']},
                                tax['date_order'],
                                round=not rounded_globally
                            )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.company_id.anglo_saxon_accounting and order.picking_id.id:
                    # Combine stock lines
                    order_pickings = self.env['stock.picking'].search([
                        '|',
                        ('origin', '=', '%s - %s' % (self.name, order.name)),
                        ('id', '=', order.picking_id.id)
                    ])
                    stock_moves = self.env['stock.move'].search([
                        ('picking_id', 'in', order_pickings.ids),
                        ('company_id.anglo_saxon_accounting', '=', True),
                        ('product_id.categ_id.property_valuation', '=', 'real_time')
                    ])
                    for move in stock_moves:
                        exp_key = move.product_id.property_account_expense_id or move.product_id.categ_id.property_account_expense_categ_id
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        amount = -sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount},
                                                                      move.picking_id.date, force_company_currency=True)
                        stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
                                                                     move.picking_id.date, force_company_currency=True)

                # Increasing current partner's customer_rank
                order.partner_id._increase_rank('customer_rank')
                # partners = (order.partner_id | order.partner_id.commercial_partner_id)
                # partners._increase_rank('customer_rank')

        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine.create(gift_card_vals)

        data.update({
            'taxes': taxes,
            'sales': sales,
            'stock_expense': stock_expense,
            'split_receivables': split_receivables,
            'combine_receivables': combine_receivables,
            'split_receivables_cash': split_receivables_cash,
            'combine_receivables_cash': combine_receivables_cash,
            'invoice_receivables': invoice_receivables,
            'stock_output': stock_output,
            'order_account_move_receivable_lines': order_account_move_receivable_lines,
            'MoveLine': MoveLine
        })
        return data

    def _get_wallet_credit_vals(self, amount, amount_converted, order):
        partial_args = {
            'name': 'Wallet Credit',
            'is_wallet': True,
            'move_id': self.move_id.id,
            'partner_id': order.partner_id._find_accounting_partner(order.partner_id).id,
            'account_id': self.config_id.wallet_account_id.id,
        }
        # partial_args['account_id'] = payment.pos_order_id.partner_id.property_account_payable_id.id,
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _get_gift_card_credit_vals(self, amount, amount_converted, order):
        partial_args = {
            'name': 'Gift Card Credit',
            'move_id': self.move_id.id,
            'partner_id': order.partner_id._find_accounting_partner(order.partner_id).id,
            'account_id': self.config_id.gift_card_account_id.id,
        }
        # partial_args['account_id'] = payment.pos_order_id.partner_id.property_account_payable_id.id,
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _get_extra_move_lines_vals(self):
        res = super(pos_session, self)._get_extra_move_lines_vals()
        if not self.config_id.enable_wallet:
            return res
        wallet_amount = {'amount': 0.0, 'amount_converted': 0.0}
        change_vals = []
        for order in self.order_ids:
            if not order.is_invoiced and order.change_amount_for_wallet > self.company_id.currency_id.round(0.0):
                wallet_amount['amount'] = order.change_amount_for_wallet
                if not self.is_in_company_currency:
                    difference = sum(self.move_id.line_ids.mapped('debit')) - sum(
                        self.move_id.line_ids.mapped('credit'))
                    wallet_amount['amount_converted'] = self.company_id.currency_id.round(difference)
                else:
                    wallet_amount['amount_converted'] = wallet_amount['amount']
                change_vals += [
                    self._get_wallet_credit_vals(wallet_amount['amount'], wallet_amount['amount_converted'], order)]
        return res + change_vals

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        partial_vals = {
            'account_id': payment.payment_method_id.receivable_account_id.id,
            'move_id': self.move_id.id,
            'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        if payment.payment_method_id.jr_use_for == 'wallet':
            partial_vals.update({
                'account_id': self.config_id.wallet_account_id.id,
                'is_wallet': True
            })
        if payment.payment_method_id.jr_use_for == 'gift_card':
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        if payment.payment_method_id.jr_use_for == 'gift_voucher':
            partial_vals.update({
                'account_id': self.config_id.gift_voucher_account_id.id,
            })

        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': payment_method.receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        if payment_method.jr_use_for == 'gift_card':
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        if payment_method.jr_use_for == 'gift_voucher':
            partial_vals.update({
                'account_id': self.config_id.gift_voucher_account_id.id,
            })
        return self._debit_amounts(partial_vals, amount, amount_converted)

    @api.model
    def take_money_in_out(self, name, amount, session_id, operation):
        if amount and operation == 'money_out':
            amount = -amount
        try:
            cash_out_obj = self.env['cash.box.out']
            total_amount = 0.0
            active_model = 'pos.session'
            active_ids = [session_id]
            if active_model == 'pos.session':
                records = self.env[active_model].browse(active_ids)
                bank_statements = [record.cash_register_id for record in records if record.cash_register_id]
                if not bank_statements:
                    raise Warning(_('There is no cash register for this PoS Session'))
                res = cash_out_obj.create({'name': name, 'amount': amount})
                return res._run(bank_statements)
            else:
                return {}
        except Exception as e:
            return {'error': 'There is no cash register for this PoS Session '}

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user_rec = self.env['res.users'].browse(self._uid)
        erp_manager_id = self.env['ir.model.data'].get_object_reference('base',
                                                                        'group_erp_manager')[1]
        if user_rec and erp_manager_id not in user_rec.groups_id.ids:
            if user_rec.store_ids:
                args += ['|', ('store_id', 'in', user_rec.store_ids.ids), ('store_id', '=', False)]
            res = super(pos_session, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        else:
            res = super(pos_session, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        return res

    # @api.multi
    def get_pos_name(self):
        if self and self.config_id:
            return self.config_id.name

    def get_inventory_details(self):
        product_product = self.env['product.product']
        stock_location = self.config_id.picking_type_id.default_location_src_id
        inventory_records = []
        final_list = []
        product_details = []
        if self and self.id:
            for order in self.order_ids:
                for line in order.lines:
                    product_details.append({
                        'id': line.product_id.id,
                        'qty': line.qty,
                    })
        custom_list = []
        for each_prod in product_details:
            if each_prod.get('id') not in [x.get('id') for x in custom_list]:
                custom_list.append(each_prod)
            else:
                for each in custom_list:
                    if each.get('id') == each_prod.get('id'):
                        each.update({'qty': each.get('qty') + each_prod.get('qty')})
        for each in custom_list:
            product_id = product_product.browse(each.get('id'))
            if product_id:
                inventory_records.append({
                    'product_id': [product_id.id, product_id.name],
                    'category_id': [product_id.id, product_id.categ_id.name],
                    'used_qty': each.get('qty'),
                    'quantity': product_id.with_context(
                        {'location': stock_location.id, 'compute_child': False}).qty_available,
                    'uom_name': product_id.uom_id.name or ''
                })
            if inventory_records:
                temp_list = []
                temp_obj = []
                for each in inventory_records:
                    if each.get('product_id')[0] not in temp_list:
                        temp_list.append(each.get('product_id')[0])
                        temp_obj.append(each)
                    else:
                        for rec in temp_obj:
                            if rec.get('product_id')[0] == each.get('product_id')[0]:
                                qty = rec.get('quantity') + each.get('quantity')
                                rec.update({'quantity': qty})
                final_list = sorted(temp_obj, key=lambda k: k['quantity'])
        return final_list or []

    # @api.multi
    def get_products_category_data(self, flag_config):
        product_list = []
        category_list = []
        if self.store_id and self.store_id.location_id.product_ids:
            for product in self.store_id.location_id.product_ids:
                product_list.append(product.id)
        if self.store_id and self.store_id.location_id.category_ids:
            for cat in self.store_id.location_id.category_ids:
                category_list.append(cat.id)
        dummy_products = self.env['product.product'].sudo().with_context(
            {'location': self.config_id.picking_type_id.default_location_src_id.id}).search(
            [('is_dummy_product', '=', True)]).ids
        if flag_config == False:
            domain = ['|', ('is_dummy_product', '=', True), ('sale_ok', '=', True), ('available_in_pos', '=', True)]
        else:
            domain = ['|', '|', ('is_dummy_product', '=', True), ('id', 'in', product_list),
                      ('pos_categ_id', 'in', category_list), ('sale_ok', '=', True), ('available_in_pos', '=', True)]
        product_records = self.env['product.product'].sudo().with_context(
            {'location': self.config_id.picking_type_id.default_location_src_id.id}).search(domain).ids
        if not product_records or len(dummy_products) >= len(product_records):
            domain = [('sale_ok', '=', True), ('available_in_pos', '=', True)]
            product_records = self.env['product.product'].sudo().with_context(
                {'location': self.config_id.picking_type_id.default_location_src_id.id}).search(domain).ids
        return product_records

    # @api.multi
    def custom_close_pos_session(self):
        self._check_pos_session_balance()
        for session in self:
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                session.action_pos_session_close()
                return True
            if session.config_id.cash_control:
                self._check_pos_session_balance()
                return self.action_pos_session_close()

    # @api.multi
    def close_open_balance(self):
        self.write({'opening_balance': False})
        return True

    # @api.multi
    def cash_control_line(self, vals):
        total_amount = 0.00
        if vals:
            self.cashcontrol_ids.unlink()
            for data in vals:
                self.env['custom.cashcontrol'].create(data)
        for cash_line in self.cashcontrol_ids:
            total_amount += cash_line.subtotal
        for statement in self.statement_ids:
            statement.write({'balance_end_real': total_amount})
        return True

    # @api.multi
    def open_balance(self, vals):
        cash_journal = []
        for statement in self.statement_ids:
            if statement.journal_id.type == 'cash':
                cash_journal.append(statement)
        if len(cash_journal) > 0:
            cash_journal[0].write({'balance_start': vals})
        return True

    def _confirm_orders(self):
        for session in self:
            company_id = session.config_id.journal_id.company_id.id
            orders = session.order_ids.filtered(lambda order: order.state == 'paid')
            journal_id = self.env['ir.config_parameter'].sudo().get_param(
                'pos.closing.journal_id_%s' % company_id, default=session.config_id.journal_id.id)

            move = self.env['pos.order'].with_context(force_company=company_id)._create_account_move(session.start_at,
                                                                                                     session.name,
                                                                                                     int(journal_id),
                                                                                                     company_id)
            orders.with_context(force_company=company_id)._create_account_move_line(session, move)
            for order in session.order_ids.filtered(lambda o: o.state not in ['done', 'invoiced']):
                if order.state not in ('draft'):
                    # raise UserError(_("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                    order.action_pos_order_done()
            orders_to_reconcile = session.order_ids._filtered_for_reconciliation()
            orders_to_reconcile.sudo()._reconcile_payments()

    # @api.multi
    def action_pos_session_open(self):
        pos_order = self.env['pos.order'].search([('state', '=', 'draft')])
        for order in pos_order:
            if order.session_id.state != 'opened':
                order.write({'session_id': self.id})
        return super(pos_session, self).action_pos_session_open()

    def _validate_session(self):
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_('This session is already closed.'))
        # self._check_if_no_draft_orders()

        # Users without any accounting rights won't be able to create the journal entry. If this
        # case, switch to sudo for creation and posting.
        sudo = False
        try:
            self._create_account_move()
        except AccessError as e:
            if self.user_has_groups('point_of_sale.group_pos_user'):
                sudo = True
                self.sudo()._create_account_move()
            else:
                raise e
        if self.move_id.line_ids:
            self.move_id.post() if not sudo else self.move_id.sudo().post()
            # Set the uninvoiced orders' state to 'done'
            self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write(
                {'state': 'done'})
        else:
            # The cash register needs to be confirmed for cash diffs
            # made thru cash in/out when sesion is in cash_control.
            if self.config_id.cash_control:
                self.cash_register_id.button_confirm_bank()
            self.move_id.unlink()
        self.write({'state': 'closed'})
        return {
            'type': 'ir.actions.client',
            'name': 'Point of Sale Menu',
            'tag': 'reload',
            'params': {'menu_id': self.env.ref('point_of_sale.menu_point_root').id},
        }

    @api.model
    def get_proxy_ip(self):
        proxy_id = self.env['res.users'].browse([self._uid]).company_id.report_ip_address
        return {'ip': proxy_id or False}

    # @api.multi
    def get_user(self):
        if self._uid == SUPERUSER_ID:
            return True

    # @api.multi
    def get_gross_total(self):
        gross_total = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    gross_total += line.qty * (line.price_unit - line.product_id.standard_price)
        return gross_total

    # @api.multi
    def get_product_cate_total(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        balance_end_real = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                if order.state != "draft":
                    for line in order.lines:
                        balance_end_real += (line.qty * line.price_unit)
            total_price_formatted = "{:.{}f}".format(balance_end_real, precision)
        return [total_price_formatted, balance_end_real]

    # @api.multi
    def get_net_gross_total(self):
        net_gross_profit = 0.0
        if self:
            net_gross_profit = self.get_gross_total() - self.get_total_tax()[1]
        return net_gross_profit

    # @api.multi
    def get_product_name(self, category_id):
        if category_id:
            category_name = self.env['pos.category'].browse([category_id]).name
            return category_name

    # @api.multi
    def get_payments(self):
        if self:
            statement_line_obj = self.env["account.bank.statement.line"]
            pos_order_obj = self.env["pos.order"]
            company_id = self.env['res.users'].browse([self._uid]).company_id.id
            pos_ids = pos_order_obj.search([('state', 'in', ['paid', 'invoiced', 'done']),
                                            ('company_id', '=', company_id), ('session_id', '=', self.id)])
            data = {}
            if pos_ids:
                pos_ids = [pos.id for pos in pos_ids]
                st_line_ids = statement_line_obj.search([('pos_statement_id', 'in', pos_ids)])
                if st_line_ids:
                    a_l = []
                    for r in st_line_ids:
                        a_l.append(r['id'])
                    self._cr.execute(
                        "select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                        "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s " \
                        "group by aj.name ", (tuple(a_l),))

                    data = self._cr.dictfetchall()
                    return data
            else:
                return {}

    # @api.multi
    def get_product_category(self):
        product_list = []
        if self and self.order_ids:
            for order in self.order_ids:
                if order.state != 'draft':
                    for line in order.lines:
                        flag = False
                        product_dict = {}
                        for lst in product_list:
                            if line.product_id.pos_categ_id:
                                if lst.get('pos_categ_id') == line.product_id.pos_categ_id.id:
                                    lst['price'] = lst['price'] + (line.qty * line.price_unit)
                                    flag = True
                            else:
                                if lst.get('pos_categ_id') == '':
                                    lst['price'] = lst['price'] + (line.qty * line.price_unit)
                                    flag = True
                        if not flag:
                            product_dict.update({
                                'pos_categ_id': line.product_id.pos_categ_id and line.product_id.pos_categ_id.id or '',
                                'price': (line.qty * line.price_unit)
                            })
                            product_list.append(product_dict)
        return product_list

    # @api.multi
    def get_journal_amount(self):
        journal_list = []
        if self and self.statement_ids:
            for statement in self.statement_ids:
                journal_dict = {}
                journal_dict.update({'journal_id': statement.journal_id and statement.journal_id.name or '',
                                     'ending_bal': statement.balance_end_real or 0.0})
                journal_list.append(journal_dict)
        return journal_list

    # @api.multi
    def get_journal_amount_x(self):
        journal_list = []
        if self and self.statement_ids:
            for statement in self.statement_ids:
                journal_dict = {}
                journal_dict.update({'journal_id': statement.journal_id and statement.journal_id.name or '',
                                     'ending_bal': statement.total_entry_encoding or 0.0})
                journal_list.append(journal_dict)
        return journal_list

    # @api.multi
    def get_total_closing(self):
        if self:
            return self.cash_register_balance_end_real

    # @api.multi
    def get_total_sales(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')

        # return [total_price_formatted, total_price]
        total_price = 0.0
        total_price_formatted = 0.0
        if self:
            for order in self.order_ids:
                if order.state != 'draft':
                    total_price += sum([(line.qty * line.price_unit) for line in order.lines])
            total_price_formatted = "{:.{}f}".format(total_price, precision)
        return [total_price_formatted, total_price]

    # @api.multi
    def get_total_tax(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total_tax = 0.0
        if self:
            pos_order_obj = self.env['pos.order']
            total_tax += sum([order.amount_tax for order in pos_order_obj.search([('session_id', '=', self.id)])])
            total_price_formatted = "{:.{}f}".format(total_tax, precision)
        return [total_price_formatted, total_tax]

    # @api.multi
    def get_vat_tax(self):
        taxes_info = {}
        taxes_details = []
        if self:
            total_tax = 0.00
            net_total = 0.00
            for order in self.order_ids:
                for line in order.lines:
                    price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_ids_after_fiscal_position.compute_all(price_unit, self.currency_id, line.qty,
                                                                           line.product_id,
                                                                           line.order_id.partner_id)['taxes']
                    price_subtotal = line.price_subtotal
                    net_total += price_subtotal
                    for tax in taxes:
                        if not taxes_info or (taxes_info and not taxes_info.get(tax['id'], False)):
                            taxes_info[tax['id']] = {'id': tax['id'],
                                                     'tax_name': tax['name'],
                                                     'tax_total': tax['amount'],
                                                     'net_total': tax['base'],
                                                     'gross_tax': tax['amount'] + tax['base']
                                                     }
                        else:
                            total_tax = tax['amount'] + taxes_info[tax['id']].get('tax_total', 0.0)
                            net_total = tax['base'] + taxes_info[tax['id']].get('net_total', 0.0)

                            taxes_info[tax['id']].update({
                                'tax_total': total_tax,
                                'net_total': net_total,
                                'gross_tax': total_tax + net_total
                            })
        for key, val in taxes_info.items():
            taxes_details.append(val)
        return taxes_details

    # @api.multi
    def get_total_discount(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total_discount = 0.0
        discount_product_id = False
        is_discount = self.config_id.module_pos_discount
        if is_discount:
            discount_product_id = self.config_id.discount_product_id.id
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100])
                    if line.product_id.id == discount_product_id:
                        total_discount += abs(line.price_subtotal_incl)
            total_price_formatted = "{:.{}f}".format(total_discount, precision)

        #                 total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100 for line in order.lines])
        return [total_price_formatted, total_discount]

    # @api.multi
    def get_total_first(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total = 0.0
        if self:
            total = ((
                             self.get_total_sales()[1] + self.get_total_tax()[1] + self.get_money_in_total()[
                         1] + self.cash_register_balance_start) + self.get_money_out_total()[1]) \
                    - (abs(self.get_total_discount()[1]))
            total_price_formatted = "{:.{}f}".format(total, precision)
        return [total_price_formatted, total]

    # @api.multi
    def get_session_date(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = timezone(self._context.get('tz'))
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%d/%m/%Y %I:%M:%S %p')

    # @api.multi
    def get_session_time(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = timezone(self._context.get('tz'))
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%I:%M:%S %p')

    # @api.multi
    def get_current_date(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            #             tz = timezone(tz)
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    # @api.multi
    def get_current_time(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            #             tz = timezone(tz)
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    # @api.multi
    def get_company_data_x(self):
        return self.user_id.company_id

    # @api.multi
    def get_current_date_x(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            #             tz = timezone(tz)
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    # @api.multi
    def get_session_date_x(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = self._context['tz']
                tz = timezone(tz)
            else:
                tz = pytz.utc
            if tz:
                #                 tz = timezone(tz)
                c_time = datetime.now(tz)
                hour_tz = int(str(c_time)[-5:][:2])
                min_tz = int(str(c_time)[-5:][3:])
                sign = str(c_time)[-6][:1]
                if sign == '+':
                    date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                                timedelta(hours=hour_tz, minutes=min_tz)
                else:
                    date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                                timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT)
            #             date_time = date_time.strftime('%Y-%m-%d')
            return date_time

    # @api.multi
    def get_current_time_x(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            #             tz = timezone(tz)
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    # @api.multi
    def get_session_time_x(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = self._context['tz']
                tz = timezone(tz)
            else:
                tz = pytz.utc
            if tz:
                #                 tz = timezone(tz)
                c_time = datetime.now(tz)
                hour_tz = int(str(c_time)[-5:][:2])
                min_tz = int(str(c_time)[-5:][3:])
                sign = str(c_time)[-6][:1]
                if sign == '+':
                    date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                                timedelta(hours=hour_tz, minutes=min_tz)
                else:
                    date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                                timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT)
            return date_time.strftime('%I:%M:%S %p')

    # @api.multi
    def get_total_sales_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total_price = 0.0
        if self:
            for order in self.order_ids:
                if order.state == 'paid':
                    for line in order.lines:
                        total_price += (line.qty * line.price_unit)
            total_price_formatted = "{:.{}f}".format(total_price, precision)
        return [total_price_formatted, total_price]

    # @api.multi
    def get_total_returns_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        pos_order_obj = self.env['pos.order']
        total_return = 0.0
        if self:
            for order in pos_order_obj.search([('session_id', '=', self.id)]):
                if order.amount_total < 0:
                    total_return += abs(order.amount_total)
            total_price_formatted = "{:.{}f}".format(total_return, precision)
        return [total_price_formatted, total_return]

    # @api.multi
    def get_total_tax_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total_tax = 0.0
        if self:
            pos_order_obj = self.env['pos.order']
            total_tax += sum([order.amount_tax for order in pos_order_obj.search([('session_id', '=', self.id)])])
            total_price_formatted = "{:.{}f}".format(total_tax, precision)
        return [total_price_formatted, total_tax]

    # @api.multi
    def get_total_discount_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        total_discount = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100 for line in order.lines])
            total_price_formatted = "{:.{}f}".format(total_discount, precision)
        return [total_price_formatted, total_discount]

    # @api.multi
    def get_total_first_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        global gross_total
        if self:
            gross_total = ((
                                   self.get_total_sales()[1] + self.get_total_tax()[1] + self.get_money_in_total()[
                               1] + self.cash_register_balance_start) + self.get_money_out_total()[1]) \
                          + self.get_total_discount()[1]
            total_price_formatted = "{:.{}f}".format(gross_total, precision)
        return [total_price_formatted, gross_total]

    # @api.multi
    def get_user_x(self):
        if self._uid == SUPERUSER_ID:
            return True

    # @api.multi
    def get_gross_total_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_cost = 0.0
        gross_total = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    total_cost += line.qty * line.product_id.standard_price
        gross_total = self.get_total_sales()[1] - \
                      + self.get_total_tax()[1] - total_cost
        total_price_formatted = "{:.{}f}".format(gross_total, precision)
        return [total_price_formatted, gross_total]

    # @api.multi
    def get_net_gross_total_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        net_gross_profit = 0.0
        total_cost = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    total_cost += line.qty * line.product_id.standard_price
            net_gross_profit = self.get_total_sales()[1] - self.get_total_tax()[1] - total_cost
            total_price_formatted = "{:.{}f}".format(net_gross_profit, precision)
        return [total_price_formatted, net_gross_profit]

    # @api.multi
    def get_product_cate_total_x(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        balance_end_real = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                if order.state == 'paid':
                    for line in order.lines:
                        balance_end_real += (line.qty * line.price_unit)
            total_price_formatted = "{:.{}f}".format(balance_end_real, precision)
        return [total_price_formatted, balance_end_real]

    # @api.multi
    def get_product_name_x(self, category_id):
        if category_id:
            category_name = self.env['pos.category'].browse([category_id]).name
            return category_name

    # @api.multi
    def get_product_category_x(self):
        product_list = []
        if self and self.order_ids:
            for order in self.order_ids:
                if order.state == 'paid':
                    for line in order.lines:
                        flag = False
                        product_dict = {}
                        for lst in product_list:
                            if line.product_id.pos_categ_id:
                                if lst.get('pos_categ_id') == line.product_id.pos_categ_id.id:
                                    lst['price'] = lst['price'] + (line.qty * line.price_unit)
                                    #                                 if line.product_id.pos_categ_id.show_in_report:
                                    lst['qty'] = lst.get('qty') or 0.0 + line.qty
                                    flag = True
                            else:
                                if lst.get('pos_categ_id') == '':
                                    lst['price'] = lst['price'] + (line.qty * line.price_unit)
                                    lst['qty'] = lst.get('qty') or 0.0 + line.qty
                                    flag = True
                        if not flag:
                            if line.product_id.pos_categ_id:
                                product_dict.update({
                                    'pos_categ_id': line.product_id.pos_categ_id and line.product_id.pos_categ_id.id or '',
                                    'price': (line.qty * line.price_unit),
                                    'qty': line.qty
                                })
                            else:
                                product_dict.update({
                                    'pos_categ_id': line.product_id.pos_categ_id and line.product_id.pos_categ_id.id or '',
                                    'price': (line.qty * line.price_unit),
                                })
                            product_list.append(product_dict)
        return product_list

    # @api.multi
    def get_payments_x(self):
        if self:
            statement_line_obj = self.env["account.bank.statement.line"]
            pos_order_obj = self.env["pos.order"]
            company_id = self.env['res.users'].browse([self._uid]).company_id.id
            pos_ids = pos_order_obj.search([('session_id', '=', self.id),
                                            ('state', 'in', ['paid', 'invoiced', 'done']),
                                            ('user_id', '=', self.user_id.id), ('company_id', '=', company_id)])
            data = {}
            if pos_ids:
                pos_ids = [pos.id for pos in pos_ids]
                st_line_ids = statement_line_obj.search([('pos_statement_id', 'in', pos_ids)])
                if st_line_ids:
                    a_l = []
                    for r in st_line_ids:
                        a_l.append(r['id'])
                    self._cr.execute(
                        "select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                        "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s " \
                        "group by aj.name ", (tuple(a_l),))

                    data = self._cr.dictfetchall()
                    return data
            else:
                return {}

    # @api.multi
    def get_money_in_total(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        if self:
            amount = 0
            account_bank_stmt_ids = self.env['account.bank.statement'].search([('pos_session_id', '=', self.id)])
            for account_bank_stmt in account_bank_stmt_ids:
                for line in account_bank_stmt.line_ids:
                    if line and line.is_money_in:
                        amount += line.amount
            total_price_formatted = "{:.{}f}".format(amount, precision)
        return [total_price_formatted, amount]

    # @api.multi
    def get_money_out_total(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        total_price_formatted = 0.0
        if self:
            amount = 0
            account_bank_stmt_ids = self.env['account.bank.statement'].search([('pos_session_id', '=', self.id)])
            for account_bank_stmt in account_bank_stmt_ids:
                for line in account_bank_stmt.line_ids:
                    if line and line.is_money_out:
                        amount += line.amount
            total_price_formatted = "{:.{}f}".format(amount, precision)
        return [total_price_formatted, amount]

    # @api.multi
    def get_money_out_details(self):
        money_out_lst = []
        precision = self.env['decimal.precision'].precision_get('Product Price')
        if self:
            account_bank_stmt_ids = self.env['account.bank.statement'].search([('pos_session_id', '=', self.id)])
            for account_bank_stmt in account_bank_stmt_ids:
                for line in account_bank_stmt.line_ids:
                    if line and line.is_money_out:
                        money_out_lst.append({
                            'name': line.name,
                            'amount': line.amount,
                        })
        for each_line in money_out_lst:
            each_line['amount'] = "{:.{}f}".format(each_line['amount'], precision)
        return money_out_lst

    # @api.multi
    def get_money_in_details(self):
        money_in_lst = []
        precision = self.env['decimal.precision'].precision_get('Product Price')
        if self:
            account_bank_stmt_ids = self.env['account.bank.statement'].search([('pos_session_id', '=', self.id)])
            for account_bank_stmt in account_bank_stmt_ids:
                for line in account_bank_stmt.line_ids:
                    if line and line.is_money_in:
                        money_in_lst.append({
                            'name': line.name,
                            'amount': line.amount,
                        })
        for each_line in money_in_lst:
            each_line['amount'] = "{:.{}f}".format(each_line['amount'], precision)
        return money_in_lst

    is_lock_screen = fields.Boolean(string="Lock Screen")

    @api.model
    def get_session_report(self):
        try:
            # sql query for get "In Progress" sessionogi
            self._cr.execute("""
                    SELECT ps.id,pc.name, ps.name FROM pos_session AS ps
                    LEFT JOIN pos_config AS pc ON ps.config_id = pc.id
                    WHERE ps.state='opened'
                """)
            session_detail = self._cr.fetchall()

            self._cr.execute(""" SELECT pc.name, ps.name, sum(pp.amount) FROM pos_session ps
                    JOIN pos_config pc on (ps.config_id = pc.id)
                    JOIN pos_payment AS pp on pp.session_id = ps.id
                    WHERE ps.state='opened'
                    GROUP BY ps.id, pc.name;""")
            session_total = self._cr.fetchall()
            #             sql query for get payments total of "In Progress" session
            lst = []
            for pay_id in session_detail:
                self._cr.execute("""
                        SELECT pc.name, ppm.name, pp.amount 
                        FROM pos_payment pp
                        LEFT JOIN pos_session AS ps on pp.session_id = ps.id
                        LEFT JOIN pos_config AS pc on ps.config_id = pc.id
                        LEFT JOIN pos_payment_method AS ppm ON  pp.payment_method_id = ppm.id
                        WHERE session_id=%s
                    """ % pay_id[0])
                bank_detail = self._cr.fetchall()
                for i in bank_detail:
                    if i[2] != None:
                        lst.append({'session_name': i[0], 'journals': i[1], 'total': i[2]})

            cate_lst = []
            for cate_id in session_detail:
                self._cr.execute("""
                        select pc.name, sum(pol.price_unit), poc.name from pos_category pc
                        join product_template pt on pc.id = pt.pos_categ_id
                        join product_product pp on pt.id = pp.product_tmpl_id
                        join pos_order_line pol on pp.id = pol.product_id
                        join pos_order po on pol.order_id = po.id
                        join pos_session ps on ps.id = po.session_id
                        join pos_config poc ON ps.config_id = poc.id
                        where po.session_id = %s
                        group by pc.name, poc.name
                    """ % cate_id[0])
                cate_detail = self._cr.fetchall()
                for j in cate_detail:
                    cate_lst.append({'cate_name': j[0], 'cate_total': j[1], 'session_name': j[2]})
            categ_null = []
            for cate_id_null in session_detail:
                self._cr.execute(""" 
                        select sum(pol.price_unit), poc.name from pos_order_line pol
                        join pos_order po on po.id = pol.order_id
                        join product_product pp on pp.id = pol.product_id
                        join product_template pt on pt.id = pp.product_tmpl_id
                        join pos_session ps on ps.id = po.session_id
                        join pos_config poc on ps.config_id = poc.id
                        where po.session_id = %s and pt.pos_categ_id is null
                        group by poc.name
                    """ % cate_id_null[0])
                categ_null_detail = self._cr.fetchall()
                for k in categ_null_detail:
                    categ_null.append({'cate_name': 'Undefined Category', 'cate_total': k[0], 'session_name': k[1]})

            all_cat = []
            for sess in session_total:
                def_cate_lst = []
                for j in cate_lst:
                    if j['session_name'] == sess[0]:
                        def_cate_lst.append(j)
                for k in categ_null:
                    if k['session_name'] == sess[0]:
                        def_cate_lst.append(k)
                all_cat.append(def_cate_lst)
            return {'session_total': session_total, 'payment_lst': lst, 'all_cat': all_cat}
        except Exception as e:
            return {'error': 'Error Function Working'}

    @api.model
    def cash_in_out_operation(self, vals):
        cash_obj = False
        if vals:
            if vals.get('operation') == "put_money":
                print("\n\n put money in operation here")
                # cash_obj = self.env['cash.box.in']
            elif vals.get('operation') == "take_money":
                cash_obj = self.env['cash.box.out']
        session_id = self.env['pos.session'].browse(vals.get('session_id'))
        if session_id:
            for session in session_id:
                bank_statements = [session.cash_register_id for session in session_id if session.cash_register_id]
            if not bank_statements:
                return {'error': _('There is no cash register for this PoS Session')}
            cntx = {'active_id': session_id.id, 'uid': vals.get('cashier')}
            res = cash_obj.with_context(cntx).create({'name': vals.get('name'), 'amount': vals.get('amount')})
            return res._run(bank_statements)
        return {'error': _('There is no cash register for this PoS Session')}

    #     @api.model
    #     def take_money_out(self, name, amount, session_id):
    #         try:
    #             cash_out_obj = self.env['cash.box.out']
    #             total_amount = 0.0
    #             active_model = 'pos.session'
    #             active_ids = [session_id]
    #             if active_model == 'pos.session':
    #                 records = self.env[active_model].browse(active_ids)
    #                 bank_statements = [record.cash_register_id for record in records if record.cash_register_id]
    #                 if not bank_statements:
    #                     raise Warning(_('There is no cash register for this PoS Session'))
    #                 res = cash_out_obj.create({'name': name, 'amount': amount})
    #                 return res._run(bank_statements)
    #             else:
    #                 return {}
    #         except Exception as e:
    #            return {'error':'There is no cash register for this PoS Session '}
    #
    #     @api.model
    #     def put_money_in(self, name, amount, session_id):
    #         try:
    #             cash_out_obj = self.env['cash.box.in']
    #             total_amount = 0.0
    #             active_model = 'pos.session'
    #             active_ids = [session_id]
    #             if active_model == 'pos.session':
    #                 records = self.env[active_model].browse(active_ids)
    #                 bank_statements = [record.cash_register_id for record in records if record.cash_register_id]
    #                 if not bank_statements:
    #                     raise Warning(_('There is no cash register for this PoS Session'))
    #                 res = cash_out_obj.create({'name': name, 'amount': amount})
    #                 return res._run(bank_statements)
    #             else:
    #                 return {}
    #         except Exception as e:
    #             return {'error':e}

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


class CashControl(models.Model):
    _name = 'custom.cashcontrol'
    _description = 'Used to Store Cash Conrtol Data.'

    coin_value = fields.Float(string="Coin/Bill Value")
    number_of_coins = fields.Integer(string="Number of Coins")
    subtotal = fields.Float(string="Subtotal")
    pos_session_id = fields.Many2one(comodel_name='pos.session', string="Session Id")


class cash_in_out_history(models.Model):
    _name = 'cash.in.out.history'
    _description = 'Used to Store Cash In-Out History.'

    user_id = fields.Many2one('res.users', string='User ID')
    session_id = fields.Many2one('pos.session', String="Session ID")
    amount = fields.Float("Amount")
    operation = fields.Selection([('Dr', 'Dr'), ('Cr', 'Cr')], string="Operation")


# Put money in from backend
# class PosBoxIn(CashBox):
#     _inherit = 'cash.box.in'
#
#     @api.model
#     def create(self, vals):
#         res = super(PosBoxIn, self).create(vals)
#         cash_out_obj_history = self.env['cash.in.out.history']
#         if res and self._context:
#             user_id = self._context.get('uid')
#             session_record_id = self._context.get('active_id')
#             history_val = {'user_id': user_id, 'session_id': session_record_id, 'amount': vals.get('amount'),
#                            'operation': 'Cr'}
#             cash_out_obj_history.create(history_val)
#         return res


# Take money out from backend
class PosBoxOut(CashBox):
    _inherit = 'cash.box.out'

    @api.model
    def create(self, vals):
        res = super(PosBoxOut, self).create(vals)
        cash_out_obj_history = self.env['cash.in.out.history']
        if res and self._context:
            user_id = self._context.get('uid')
            session_record_id = self._context.get('active_id')
            history_val = {'user_id': user_id, 'session_id': session_record_id, 'amount': vals.get('amount'),
                           'operation': 'Dr'}
            cash_out_obj_history.create(history_val)
        return res


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_html_report(self, id, report_name):
        report = self._get_report_from_name(report_name)
        document = report.render_qweb_html([id], data={})
        if document:
            return document
        return False


class Website(models.Model):
    _inherit = 'website'

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        if self.env.user:
            return super(Website, self).sale_get_order(force_create=False, code=None, update_pricelist=False,
                                                       force_pricelist=False)
        else:
            return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
