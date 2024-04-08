# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    qr_product_id = fields.Many2one('product.product', string='Product')
    qr_account_tax_id = fields.Many2one('account.tax', string="Tax")
