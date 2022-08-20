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


from odoo import models, fields, api, _
from odoo.tools import float_compare, float_round


class BomOrderLineBomLine(models.Model):
    _name = 'pos.orderline.bom.line'
    _description = 'bom order line'

    prod_bom_id = fields.Many2one("mrp.bom", "Product in Bill Of Materials")
    pos_order_line_id = fields.Many2one("pos.order.line", "Order Line")
    bom_line_id = fields.Many2one('mrp.bom.line', "BOM line")
    qty = fields.Float("QTY")
    product_id = fields.Many2one('product.product', 'Modifier Name', required=True)
    pos_mrp_id = fields.Many2one('mrp.production')


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    pos_bom_line_ids = fields.One2many('pos.orderline.bom.line', 'pos_mrp_id', string='')
    line_ref = fields.Char("Mo ref")
    pos_order_id = fields.Many2one("pos.order", string="Pos Order")

    @api.model
    def create(self, values):
        res = super(MrpProduction, self).create(values)
        res._onchange_move_raw()
        return res


class MrpProductProduce(models.TransientModel):
    _inherit = "mrp.product.produce"

    @api.onchange('qty_producing')
    def _onchange_product_qty(self):
        lines = []
        qty_todo = self.product_uom_id._compute_quantity(
            self.production_id.product_qty, self.production_id.product_uom_id, round=False)
        for move in self.production_id.move_raw_ids.filtered(
                lambda m: m.state not in ('done', 'cancel') and m.bom_line_id):
            qty_to_consume = float_round(
                qty_todo * move.unit_factor, precision_rounding=move.product_uom.rounding)
            for move_line in move.move_line_ids:
                to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty)
                lines.append({
                    'move_id': move.id,
                    'qty_to_consume': to_consume_in_line,
                    'qty_done': to_consume_in_line,
                    'lot_id': move_line.lot_id.id,
                    'product_uom_id': move.product_uom.id,
                    'product_id': move.product_id.id,
                    'qty_reserved': min(to_consume_in_line, move_line.product_uom_qty),
                })
                qty_to_consume -= to_consume_in_line
            if float_compare(
                    qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                if move.product_id.tracking == 'serial':
                    while float_compare(
                            qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                        lines.append({
                            'move_id': move.id,
                            'qty_to_consume': 1,
                            'qty_done': 1,
                            'product_uom_id': move.product_uom.id,
                            'product_id': move.product_id.id,
                        })
                        qty_to_consume -= 1
                else:
                    lines.append({
                        'move_id': move.id,
                        'qty_to_consume': qty_to_consume,
                        'qty_done': qty_to_consume,
                        'product_uom_id': move.product_uom.id,
                        'product_id': move.product_id.id,
                    })
        for line in self.production_id.pos_bom_line_ids:
            for data in lines:
                if data.get('product_id') == line.product_id.id:
                    data['qty_done'] = line.qty
        self.raw_workorder_line_ids = [(5,)] + [(0, 0, x) for x in lines]

    # @api.onchange('product_qty')
    # def _onchange_product_qty(self):
    #     lines = []
    #     qty_todo = self.product_uom_id._compute_quantity(self.product_qty, self.production_id.product_uom_id,
    #                                                      round=False)
    #     for move in self.production_id.move_raw_ids.filtered(
    #             lambda m: m.state not in ('done', 'cancel') and m.bom_line_id):
    #         qty_to_consume = float_round(qty_todo * move.unit_factor, precision_rounding=move.product_uom.rounding)
    #         for move_line in move.move_line_ids:
    #             if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) <= 0:
    #                 break
    #             if move_line.lot_produced_id or float_compare(move_line.product_uom_qty, move_line.qty_done,
    #                                                           precision_rounding=move.product_uom.rounding) <= 0:
    #                 continue
    #             to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty)
    #             lines.append({
    #                 'move_id': move.id,
    #                 'qty_to_consume': to_consume_in_line,
    #                 'qty_done': to_consume_in_line,
    #                 'lot_id': move_line.lot_id.id,
    #                 'product_uom_id': move.product_uom.id,
    #                 'product_id': move.product_id.id,
    #                 'qty_reserved': min(to_consume_in_line, move_line.product_uom_qty),
    #             })
    #             qty_to_consume -= to_consume_in_line
    #         if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
    #             if move.product_id.tracking == 'serial':
    #                 while float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
    #                     lines.append({
    #                         'move_id': move.id,
    #                         'qty_to_consume': 1,
    #                         'qty_done': 1,
    #                         'product_uom_id': move.product_uom.id,
    #                         'product_id': move.product_id.id,
    #                     })
    #                     qty_to_consume -= 1
    #             else:
    #                 lines.append({
    #                     'move_id': move.id,
    #                     'qty_to_consume': qty_to_consume,
    #                     'qty_done': qty_to_consume,
    #                     'product_uom_id': move.product_uom.id,
    #                     'product_id': move.product_id.id,
    #                 })
    #     for line in self.production_id.pos_bom_line_ids:
    #         for data in lines:
    #             if data.get('product_id') == line.product_id.id:
    #                 data['qty_done'] = line.qty
    #     self.produce_line_ids = [(5,)] + [(0, 0, x) for x in lines]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
