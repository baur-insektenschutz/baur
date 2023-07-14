# -*- coding: utf-8 -*-
# Powered by Mindphin Technologies.
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product_template"

    farbe = fields.Char(string="Farbe")
    grosse = fields.Char(string="Grosse")
