# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    execution = fields.Char(string="Execution", readonly=True)

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.execution"""
        return res

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['execution'] = "s.execution"
        return res