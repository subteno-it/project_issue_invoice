# -*- coding: utf-8 -*-
##############################################################################
#
#    project_issue_invoice module for OpenERP, Create
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.syleam.fr/>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#
#    This file is a part of project_issue_invoice
#
#    project_issue_invoice is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    project_issue_invoice is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools.translate import _
from openerp import models, api, fields


class ProjectIssueInvoice(models.Model):
    _name = 'project.issue.invoice'
    _description = 'Invoice Project Issue'
    _order = 'sequence, id'

    project_id = fields.Many2one('project.project', string='Project Reference', required=True, select=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10, help='Gives the sequence order when displaying a list of project issue invoice.')
    tag_id = fields.Many2one(comodel_name='project.tags', string='Tags')
    product_id = fields.Many2one('product.product', string='Product', required=True, help='Product used for calculate the price for the invoice')
    name = fields.Char(string='Description', size=256, required=True, select=True, help='Decription used for the name of invoice line')
    notes = fields.Text(string='Notes')
    quantity = fields.Integer(string='Quantity', default=0.0, help='Quantity minimum to invoice')
    price_fixed = fields.Boolean(string='Price Fixed ?', default=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('project.issue.invoice'), help='Company of the project issue')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            if self.product_id.description_sale:
                self.notes = self.product_id.description_sale


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    @api.one
    @api.depends('account_invoice_id.state')
    def _compute_issue_invoiced(self):
        self.issue_invoiced = self.account_invoice_id.state != 'cancel'

    invoiced = fields.Boolean(string='Invoiced', default=False, help='Indicate if the issue is invoiced or not')
    issue_invoiced = fields.Boolean(string='Invoiced', default=False, compute='_compute_issue_invoiced', store=True, help='Indicate if the issue has already an invoice')
    account_invoice_id = fields.Many2one('account.invoice', string='Account Invoice', help='Account Invoice')

    @api.multi
    def write(self, values):
        """
        We cannot modify when the issue is invoiced
        """
        assert(all(not issue.issue_invoiced for issue in self), _('You cannot modify an invoiced issue !'))
        return super(ProjectIssue, self).write(values)

    @api.model
    def search_issue2invoice(self, project_ids):
        """
        This method search all issues not invoiced with project_id in selection
        """
        if project_ids:
            return self.search([
                ('invoiced', '=', False),
                ('stage_id.closed', '=', True),
                ('project_id', 'in', project_ids)
            ])
        else:
            return []

    @api.model
    def make_invoice(self, issues=None, projects=None):
        if issues or projects:
            if projects is None:
                projects = []
            invoice_obj = self.env['account.invoice']
            invoice_line_obj = self.env['account.invoice.line']
            project_issue_invoice_obj = self.env['project.issue.invoice']
            if issues:
                projects = list(set(projects) | set([issue.project_id for issue in issues if issue.project_id]))
            invoice_ids = self.env['account.invoice']
            # Field for know the categ already invoiced
            categ_used_ids = []
            for project in projects:
                # Prepare invoice
                vals = {'partner_id': project.partner_id.id,
                        'type': 'out_invoice',
                        'name': '-',
                        'currency_id': self.env.user.company_id.currency_id.id,
                        }
                # new creates a temporary record to apply the on_change afterwards
                invoice = invoice_obj.new(vals)
                invoice._onchange_partner_id()
                invoice_vals = {
                    'name': project.name,
                    'account_id': invoice.account_id.id,
                    'partner_id': project.partner_id.id,
                    'payment_term_id': invoice.payment_term_id.id,
                    'fiscal_position_id': invoice.fiscal_position_id.id,
                }
                invoice_id = invoice_obj.create(invoice_vals)
                invoice_ids |= invoice_id
                # Create invoice line for the lines of project issue invoice with price fixed
                invoice_issue_ids = project_issue_invoice_obj.search([
                    ('project_id', '=', project.id),
                    ('price_fixed', '=', True)
                ])
                pricelist_id = project.partner_id.property_product_pricelist.id
                for invoice_issue in invoice_issue_ids:
                    # Prepare invoice
                    vals = {'product_id': invoice_issue.product_id.id,
                            'partner_id': project.partner_id.id,
                            }
                    # new creates a temporary record to apply the on_change afterwards
                    invoice_line = invoice_line_obj.new(vals)
                    invoice_line._onchange_product_id()
                    price = project.partner_id.property_product_pricelist.price_get(
                        invoice_issue.product_id.id,
                        invoice_issue.quantity,
                        project.partner_id.id
                    )[pricelist_id]
                    invoice_line_obj.create({
                        'name': invoice_issue.name,
                        'invoice_id': invoice_id.id,
                        'account_id': invoice_line.account_id.id,
                        'account_analytic_id': project.analytic_account_id.id,
                        'price_unit': price,
                        'quantity': invoice_issue.quantity,
                        'invoice_line_tax_ids': [(6, 0, invoice_line.invoice_line_tax_ids.mapped('id'))],
                        'product_id': invoice_issue.product_id.id,
                    })
                # Create invoice line for the lines of project issue invoice without price fixed
                invoice_issue_ids = project_issue_invoice_obj.search([
                    ('project_id', '=', project.id),
                    ('price_fixed', '=', False)
                ])
                for invoice_issue in invoice_issue_ids:
                    # Prepare invoice
                    vals = {'product_id': invoice_issue.product_id.id,
                            'partner_id': project.partner_id.id,
                            }
                    # new creates a temporary record to apply the on_change afterwards
                    invoice_line = invoice_line_obj.new(vals)
                    invoice_line._onchange_product_id()
                    duration = 0.0
                    # If quantity > 0 then we must invoice 1 line
                    if invoice_issue.quantity > 0:
                        price = project.partner_id.property_product_pricelist.price_get(
                            invoice_issue.product_id.id,
                            invoice_issue.quantity,
                            project.partner_id.id
                        )[pricelist_id]
                        invoice_line_obj.create({
                            'name': invoice_issue.name,
                            'invoice_id': invoice_id.id,
                            'account_id': self.account_id.id,
                            'account_analytic_id': project.analytic_account_id.id,
                            'price_unit': price,
                            'quantity': invoice_issue.quantity,
                            'invoice_line_tax_ids': [(6, 0, invoice_line.invoice_line_tax_ids.mapped('id'))],
                            'product_id': invoice_issue.product_id.id,
                        })
                        duration -= invoice_issue.quantity
                    if invoice_issue.tag_id and invoice_issue.tag_id.id:
                        categ_used_ids.append(invoice_issue.tag_id.id)
                        issue_categ_ids = self.search([
                            ('project_id', '=', project.id),
                            ('tag_ids', 'in', (invoice_issue.tag_id.id)),
                            ('id', 'in', [issue.id for issue in issues])
                        ])
                        issue_categ_ids.write({
                            'account_invoice_id': invoice_id.id,
                            'invoiced': True
                        })
                    elif categ_used_ids:
                        issue_categ_ids = self.search([
                            ('project_id', '=', project.id),
                            ('tag_ids', 'not in', categ_used_ids),
                            ('id', 'in', issues.mapped('id'))
                        ])
                        issue_categ_ids.write({
                            'account_invoice_id': invoice_id.id,
                            'invoiced': True
                        })
                    else:
                        issue_categ_ids = self.search([
                            ('project_id', '=', project.id),
                            ('id', 'in', issues.mapped('id'))
                        ])
                        issue_categ_ids.write({
                            'account_invoice_id': invoice_id.id,
                            'invoiced': True
                        })
                    for issue_categ in issue_categ_ids:
                        duration += issue_categ.duration_timesheet
                    # If duration > 0, the duration of all tickets not invoiced for this category is more than the quantity indicate in project issue invoice so invoice the difference.
                    if duration > 0:
                        price = project.partner_id.property_product_pricelist.price_get(
                            invoice_issue.product_id.id,
                            duration,
                            project.partner_id.id
                        )[pricelist_id]
                        invoice_line_obj.create({
                            'name': invoice_issue.name,
                            'invoice_id': invoice_id.id,
                            'account_id': invoice_line.account_id.id,
                            'account_analytic_id': project.analytic_account_id.id,
                            'price_unit': price,
                            'quantity': duration,
                            'invoice_line_tax_ids': [(6, 0, invoice_line.invoice_line_tax_ids.mapped('id'))],
                            'product_id': invoice_issue.product_id.id,
                        })

            # Compute the amount of invoice
            if invoice_ids:
                invoice_ids.compute_taxes()
            return invoice_ids
        else:
            return False

    @api.model
    def run_scheduler(self):
        ''' Runs through scheduler.
        @param use_new_cursor: False or the dbname
        '''
        project_ids = self.env['project.project'].search([
            ('invoice_issue_policy', '=', 'manual'),
            ('state', '=', 'open')
        ])
        issue_ids = self.search_issue2invoice(project_ids.mapped('id'))
        # Search all project with lines with price fixed
        issue_inv_ids = self.env['project.issue.invoice'].search([
            ('project_id', 'in', project_ids.mapped('id')),
            ('quantity', '>', 0.0),
        ])
        issue_inv_data = issue_inv_ids.read(['project_id'])
        project_ids = list(set([data['project_id'][0] for data in issue_inv_data if data['project_id']]))
        if issue_ids or project_ids:
            self.make_invoice(issue_ids, project_ids)

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if self.stage_id.closed and self.project_id.invoice_issue_policy == 'auto':
            self.make_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
