# -*- coding: utf-8 -*-
# Powered by Mindphin Technologies.

from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from odoo.tools import format_date, formatLang, frozendict



class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def _default_example_amount(self):
        invoice = self.env['account.move'].search([('id', '=', self._context.get('invoice_id'))])
        return invoice.amount_total or 100  # Force default value if the context is set to False

    def _default_example_date(self):
        return self._context.get('example_date') or fields.Date.today()

    display_terms = fields.Boolean(string="Display terms on invoice")
    example_amount = fields.Float(default=_default_example_amount, store=False)
    example_date = fields.Date(string='Date example', default=_default_example_date, store=False)
    example_invalid = fields.Boolean(compute='_compute_example_invalid')
    example_preview = fields.Html(compute='_compute_example_preview')

    @api.depends('line_ids')
    def _compute_example_invalid(self):
        for payment_term in self:
            payment_term.example_invalid = len(payment_term.line_ids.filtered(lambda l: l.value == 'balance')) != 1

    @api.depends('example_amount', 'example_date', 'line_ids.value', 'line_ids.value_amount',
                 'line_ids.days')
    def _compute_example_preview(self):
        for record in self:
            example_preview = ""
            if not record.example_invalid:
                currency = self.env.company.currency_id
                terms = record._compute_terms(
                    date_ref=record.example_date,
                    currency=currency,
                    company=self.env.company,
                    tax_amount=0,
                    tax_amount_currency=0,
                    untaxed_amount=record.example_amount,
                    untaxed_amount_currency=record.example_amount,
                    sign=1)
                for i, info_by_dates in enumerate(record._get_amount_by_date(terms, currency).values()):
                    date = info_by_dates['date']
                    discount_date = info_by_dates['discount_date']
                    amount = info_by_dates['amount']
                    discount_amount = info_by_dates['discounted_amount'] or 0.0
                    example_preview += f"""
                        <div style='margin-left: 20px;'>
                            <b>{i+1}#</b>
                            Installment of
                            <b>{formatLang(self.env, amount, monetary=True, currency_obj=currency)}</b>
                            on 
                            <b style='color: #704A66;'>{date}</b>
                    """
                    if discount_date:
                        example_preview += f"""
                         (<b>{formatLang(self.env, discount_amount, monetary=True, currency_obj=currency)}</b> if paid before <b>{format_date(self.env, terms[i].get('discount_date'))}</b>)
                    """
                    example_preview += "</div>"

            record.example_preview = example_preview
    @api.model
    def _get_amount_by_date(self, terms, currency):
        """
        Returns a dictionary with the amount for each date of the payment term
        (grouped by date, discounted percentage and discount last date,
        sorted by date and ignoring null amounts).
        """
        terms = sorted(terms, key=lambda t: t.get('date'))
        amount_by_date = {}
        for term in terms:
            key = frozendict({
                'date': term['date'],
                'discount_date': term['discount_date'],
                'discount_percentage': term['discount_percentage'],
            })
            results = amount_by_date.setdefault(key, {
                'date': format_date(self.env, term['date']),
                'amount': 0.0,
                'discounted_amount': 0.0,
                'discount_date': format_date(self.env, term['discount_date']),
            })
            results['amount'] += term['foreign_amount']
            results['discounted_amount'] += term['discount_amount_currency']
        return amount_by_date

    @api.constrains('line_ids')
    def _check_lines(self):
        for terms in self:
            if len(terms.line_ids.filtered(lambda r: r.value == 'balance')) != 1:
                raise ValidationError(_('The Payment Term must have one Balance line.'))
            if terms.line_ids.filtered(lambda r: r.value == 'fixed' and r.discount_percentage):
                raise ValidationError(_("You can't mix fixed amount with early payment percentage"))

    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency):
        """Get the distribution of this payment term.
        :param date_ref: The move date to take into account
        :param currency: the move's currency
        :param company: the company issuing the move
        :param tax_amount: the signed tax amount for the move
        :param tax_amount_currency: the signed tax amount for the move in the move's currency
        :param untaxed_amount: the signed untaxed amount for the move
        :param untaxed_amount_currency: the signed untaxed amount for the move in the move's currency
        :param sign: the sign of the move
        :return (list<tuple<datetime.date,tuple<float,float>>>): the amount in the company's currency and
            the document's currency, respectively for each required payment date
        """
        self.ensure_one()
        company_currency = company.currency_id
        tax_amount_left = tax_amount
        tax_amount_currency_left = tax_amount_currency
        untaxed_amount_left = untaxed_amount
        untaxed_amount_currency_left = untaxed_amount_currency
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        result = []

        for line in self.line_ids.sorted(lambda line: line.value == 'balance'):
            term_vals = {
                'date': line._get_due_date(date_ref),
                'has_discount': line.discount_percentage,
                'discount_date': None,
                'discount_amount_currency': 0.0,
                'discount_balance': 0.0,
                'discount_percentage': line.discount_percentage,
            }

            if line.value == 'fixed':
                term_vals['company_amount'] = sign * company_currency.round(line.value_amount)
                term_vals['foreign_amount'] = sign * currency.round(line.value_amount)
                company_proportion = tax_amount/untaxed_amount if untaxed_amount else 1
                foreign_proportion = tax_amount_currency/untaxed_amount_currency if untaxed_amount_currency else 1
                line_tax_amount = company_currency.round(line.value_amount * company_proportion) * sign
                line_tax_amount_currency = currency.round(line.value_amount * foreign_proportion) * sign
                line_untaxed_amount = term_vals['company_amount'] - line_tax_amount
                line_untaxed_amount_currency = term_vals['foreign_amount'] - line_tax_amount_currency
            elif line.value == 'percent':
                term_vals['company_amount'] = company_currency.round(total_amount * (line.value_amount / 100.0))
                term_vals['foreign_amount'] = currency.round(total_amount_currency * (line.value_amount / 100.0))
                line_tax_amount = company_currency.round(tax_amount * (line.value_amount / 100.0))
                line_tax_amount_currency = currency.round(tax_amount_currency * (line.value_amount / 100.0))
                line_untaxed_amount = term_vals['company_amount'] - line_tax_amount
                line_untaxed_amount_currency = term_vals['foreign_amount'] - line_tax_amount_currency
            else:
                line_tax_amount = line_tax_amount_currency = line_untaxed_amount = line_untaxed_amount_currency = 0.0

            tax_amount_left -= line_tax_amount
            tax_amount_currency_left -= line_tax_amount_currency
            untaxed_amount_left -= line_untaxed_amount
            untaxed_amount_currency_left -= line_untaxed_amount_currency

            if line.value == 'balance':
                term_vals['company_amount'] = tax_amount_left + untaxed_amount_left
                term_vals['foreign_amount'] = tax_amount_currency_left + untaxed_amount_currency_left
                line_tax_amount = tax_amount_left
                line_tax_amount_currency = tax_amount_currency_left
                line_untaxed_amount = untaxed_amount_left
                line_untaxed_amount_currency = untaxed_amount_currency_left

            if line.discount_percentage:
                if company.early_pay_discount_computation in ('excluded', 'mixed'):
                    term_vals['discount_balance'] = company_currency.round(term_vals['company_amount'] - line_untaxed_amount * line.discount_percentage / 100.0)
                    term_vals['discount_amount_currency'] = currency.round(term_vals['foreign_amount'] - line_untaxed_amount_currency * line.discount_percentage / 100.0)
                else:
                    term_vals['discount_balance'] = company_currency.round(term_vals['company_amount'] * (1 - (line.discount_percentage / 100.0)))
                    term_vals['discount_amount_currency'] = currency.round(term_vals['foreign_amount'] * (1 - (line.discount_percentage / 100.0)))
                term_vals['discount_date'] = date_ref + relativedelta(days=line.discount_days)

            result.append(term_vals)
        return result


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    months = fields.Integer(string='Months', required=True, default=0)
    end_month = fields.Boolean(string='End of month', help="Switch to end of the month after having added months or days")
    discount_percentage = fields.Float(string='Discount %', help='Early Payment Discount granted for this line')


    def _get_due_date(self, date_ref):
        self.ensure_one()
        due_date = fields.Date.from_string(date_ref)
        due_date += relativedelta(months=self.months)
        due_date += relativedelta(days=self.days)
        if self.end_month:
            due_date += relativedelta(day=31)
            due_date += relativedelta(days=self.days_after)
        return due_date


class TextBlocks(models.Model):
    _name = 'text.blocks'

    name = fields.Char('Text-block Name')
    text_block = fields.Html('Text-block Text')


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    x_studio_lieferfrist = fields.Selection(
        [
            ('ca. 6 Wochen', 'ca. 6 Wochen'),
            ('ca. 8 Wochen', 'ca. 8 Wochen'),
            ('6 - 8 Wochen', '6 - 8 Wochen'),
            ('8 - 10 Wochen', '8 - 10 Wochen'),
            ('4 Wochen', '4 Wochen'),
            ('ca. 4 Wochen, wird abgeholt in Uttigen', 'ca. 4 Wochen, wird abgeholt in Uttigen'),
            ('ca. 4 Wochen, wird geliefert', 'ca. 4 Wochen, wird geliefert'),
            ('ca. 3 bis 4 Wochen', 'ca. 3 bis 4 Wochen'),
            ('4 - 6 Wochen', '4 - 6 Wochen'),
        ]
    )
    x_studio_preise_inkl_montage = fields.Boolean(string="Preise inkl. Montage")
    termin = fields.Boolean(string="Termin")
    abholung = fields.Boolean(string="Abholung")
    preise_sonderfarben = fields.Boolean(string="Preise Sonderfarben")
    preise_exkl_montage = fields.Boolean(string="Preise exkl. Montage")
    rabatt_5 = fields.Boolean(string="Rabatt 5%")
    rabatt_10 = fields.Boolean(string="Rabatt 10%")
    rabatt_40 = fields.Boolean(string="Rabatt 40%")
    rabatt_u = fields.Boolean(string="Rabatt U")
    rabattierung = fields.Boolean(string="Rabattierung")
    garantie = fields.Boolean(string="Garantie")
    garantie_wiederverkaufer = fields.Boolean(string="Garantie Wiederverkäufer")
    freier_text_block_id = fields.Many2one('text.blocks', 'Freier Text Block')
    freier_text = fields.Html('Freier Text')

    @api.onchange('freier_text_block_id')
    def onchange_freier_text_block_id(self):
        if self.freier_text_block_id:
            self.freier_text = self.freier_text_block_id.text_block


class SaleOrder(models.Model):
    _inherit = "sale.order"

    termin = fields.Boolean(string="Termin")
    abholung = fields.Boolean(string="Abholung")
    preise_sonderfarben = fields.Boolean(string="Preise Sonderfarben")
    preise_exkl_montage = fields.Boolean(string="Preise exkl. Montage")
    rabatt_5 = fields.Boolean(string="Rabatt 5%")
    rabatt_10 = fields.Boolean(string="Rabatt 10%")
    rabatt_40 = fields.Boolean(string="Rabatt 40%")
    rabatt_u = fields.Boolean(string="Rabatt U")
    rabattierung = fields.Boolean(string="Rabattierung")
    garantie = fields.Boolean(string="Garantie")
    garantie_wiederverkaufer = fields.Boolean(string="Garantie Wiederverkäufer")
    freier_text_block_id = fields.Many2one('text.blocks', 'Freier Text Block')
    freier_text = fields.Html('Freier Text')

    @api.onchange('freier_text_block_id')
    def onchange_freier_text_block_id(self):
        if self.freier_text_block_id:
            self.freier_text = self.freier_text_block_id.text_block

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        res = super(SaleOrder, self).onchange_sale_order_template_id()
        if self.sale_order_template_id:
            template = self.sale_order_template_id
            if template.x_studio_lieferfrist:
                self.x_studio_lieferfrist = template.x_studio_lieferfrist
            if template.x_studio_preise_inkl_montage:
                self.x_studio_preise_inkl_montage = template.x_studio_preise_inkl_montage
            if template.termin:
                self.termin = template.termin
            if template.abholung:
                self.abholung = template.abholung
            if template.preise_sonderfarben:
                self.preise_sonderfarben = template.preise_sonderfarben
            if template.preise_exkl_montage:
                self.preise_exkl_montage = template.preise_exkl_montage
            if template.rabatt_5:
                self.rabatt_5 = template.rabatt_5
            if template.rabatt_10:
                self.rabatt_10 = template.rabatt_10
            if template.rabatt_40:
                self.rabatt_40 = template.rabatt_40
            if template.rabatt_u:
                self.rabatt_u = template.rabatt_u
            if template.rabattierung:
                self.rabattierung = template.rabattierung
            if template.garantie:
                self.garantie = template.garantie
            if template.garantie_wiederverkaufer:
                self.garantie_wiederverkaufer = template.garantie_wiederverkaufer
            if template.freier_text_block_id:
                self.freier_text_block_id = template.freier_text_block_id
            if template.freier_text:
                self.freier_text = template.freier_text
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            if self.product_id.farbe:
                self.x_studio_farbe = self.product_id.farbe
            if self.product_id.grosse:
                self.x_studio_groesse = self.product_id.grosse
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    garantie = fields.Boolean(string="Garantie")
    garantie_wiederverkaufer = fields.Boolean(string="Garantie Wiederverkäufer")
    freier_text_block_id = fields.Many2one('text.blocks', 'Freier Text Block')
    freier_text = fields.Html('Freier Text')

    @api.onchange('freier_text_block_id')
    def onchange_freier_text_block_id(self):
        if self.freier_text_block_id:
            self.freier_text = self.freier_text_block_id.text_block
