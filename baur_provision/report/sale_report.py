# -*- coding: utf-8 -*-
# Powered by Mindphin Technologies.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    vermittelt_durch_id = fields.Many2one('res.partner', '(sd) vermittelt durch', readonly=True)


    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.vermittelt_durch_id"""
        return res


    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['vermittelt_durch_id'] = "s.vermittelt_durch_id"
        return res



class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    vermittelt_durch_id = fields.Many2one('res.partner', '(sd) vermittelt durch', readonly=True)

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", move.vermittelt_durch_id as vermittelt_durch_id"
