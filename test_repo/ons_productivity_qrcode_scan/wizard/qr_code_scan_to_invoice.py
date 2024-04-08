#  -*- coding: utf-8 -*-
#
# Copyright (c) 2018-TODAY Open-Net Ltd. All rights reserved.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api
from odoo.exceptions import UserError


class QrCodeScanToInvoice(models.TransientModel):
    _name = "qrcode.scan"
    _description = "Generation of a draft invoice from a paper QR code invoice"

    qrcode_value = fields.Text(string='Valeur du QR')

    def generate_invoice_from_qrcode(self):

        acc_move = {}
        supplier_info = {}

        qr_values_tab = self.qrcode_value.split('\n')

        # Supplier infos
        supplier_info['iban'] = qr_values_tab[3]
        supplier_info['address_type'] = qr_values_tab[4]
        supplier_info['name'] = qr_values_tab[5]
        # ------------------------

        # Account move type
        acc_move['move_type'] = 'in_invoice'

        # Address Type
        if supplier_info['address_type'] == 'K':
            supplier_info['street'] = qr_values_tab[6]
            supplier_info['zip'] = qr_values_tab[7].split()[0]
            supplier_info['city'] = qr_values_tab[7].split()[1]
        elif supplier_info['address_type'] == 'S':
            supplier_info['street'] = qr_values_tab[6] + " " + qr_values_tab[7]
            supplier_info['zip'] = qr_values_tab[8]
            supplier_info['city'] = qr_values_tab[9]
        else:
            raise UserError("Unknown address type.")
        # ------------------------

        # Account move partner_id
        supplier = self.env['res.partner'].search([('name', 'ilike', supplier_info['name']), ('street', 'ilike', supplier_info['street']), ('zip', 'ilike', supplier_info['zip']), ('city', 'ilike', supplier_info['city'])], limit=1)

        if supplier:
            supp_id = supplier.id
            acc_move['partner_id'] = supp_id
        else:
            supp_id = self.env['res.partner'].create({'name': supplier_info['name'], 'street': supplier_info['street'], 'zip': supplier_info['zip'], 'city': supplier_info['city']}).id
            acc_move['partner_id'] = supp_id
        # ------------------------

        # Iban
        bank_id = self.env['res.partner.bank'].search([('acc_number', '=', supplier_info['iban']), ('partner_id', '=', supplier.id)], limit=1)
        existing_number_bank_id = self.env['res.partner.bank'].search([('acc_number', '=', supplier_info['iban'])], limit=1)

        if not bank_id and existing_number_bank_id:
            raise UserError("It seems that the IBAN already exists despite the fact that this debtor does not exist in your database. Please check the name and address of the supplier.")

        if not bank_id:
            bank_id = self.env['res.partner.bank'].create({'acc_number': supplier_info['iban'], 'partner_id': supp_id})

        acc_move['partner_bank_id'] = bank_id.id
        # ------------------------

        # Reference payment
        acc_move['payment_reference'] = qr_values_tab[28] or qr_values_tab[29]

        # Create account move line
        pid = False
        if supplier.qr_product_id:
            pid = supplier.qr_product_id
        elif self.env.user.company_id.qr_product_id:
            pid = self.env.user.company_id.qr_product_id
        else:
            raise UserError("Please define QR product on company (account tab)")

        tax = False
        if supplier.qr_account_tax_id:
            tax = supplier.qr_account_tax_id
        elif self.env.user.company_id.qr_account_tax_id:
            tax = self.env.user.company_id.qr_account_tax_id
        else:
            raise UserError("Please define QR tax on company (account tab)")

        account_move_line_dict = {
            'product_id': pid,
            'tax_ids': tax,
            'price_unit': qr_values_tab[18]
        }

        acc_move['invoice_line_ids'] = [
            (0, 0, account_move_line_dict)
        ]
        # ------------------------

        res = self.env['account.move'].create(acc_move)

        return {
            'name': res.name,
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': res.id,
            'type': 'ir.actions.act_window',
            }
