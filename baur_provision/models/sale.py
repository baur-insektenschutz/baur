# -*- coding: utf-8 -*-
# Powered by Mindphin Technologies.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    vermittelt_durch_id = fields.Many2one('res.partner', string="(sd) vermittelt durch")

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)
        res.vermittelt_durch_id = self.vermittelt_durch_id if self.vermittelt_durch_id else None
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    vermittelt_durch_id = fields.Many2one('res.partner', string="(sd) vermittelt durch")


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        res = super(SaleAdvancePaymentInv, self)._prepare_invoice_values(order, name, amount, so_line)
        res['vermittelt_durch_id'] = order.vermittelt_durch_id if order.vermittelt_durch_id else None
        return res


class ResPartner(models.Model):
    _inherit = "res.partner"

    vermittelt_durch = fields.Boolean(string="(sd) Provisionsberechtigt")
