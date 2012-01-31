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

from osv import osv
from osv import fields
from tools.translate import _
import pooler

class project_issue_invoice(osv.osv):
    _name = 'project.issue.invoice'
    _description = 'Invoice Project Issue'
    _order = 'sequence, id'

    _columns = {
        'project_id': fields.many2one('project.project', 'Project Reference', required=True, select=True, readonly=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of project issue invoice." ),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('object_id.model', '=', 'project.issue')]", help="If empty, this line will be used for all categories's issue."),
        'product_id': fields.many2one('product.product', 'Product', required=True, help="Product used for calculate the price for the invoice" ),
        'name': fields.char('Description', size=256, required=True, select=True, help="Decription used for the name of invoice line"),
        'notes': fields.text('Notes'),
        'quantity': fields.float('Quantity', help="Quantity minimum to invoice" ),
        'price_fixed': fields.boolean('Price Fixed ?', ),
        'active': fields.boolean('Active', ),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, help='Company of the project issue'),
    }

    _defaults = {
        'quantity': 0.0,
        'active': True,
        'price_fixed': False,
        'sequence': 10,
        'company_id': lambda self, cr, uid, c = None: self.pool.get('res.company')._company_default_get(cr, uid, 'project.issue.invoice', context=c),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """
        Fill name and note from fields's product
        """
        result = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if product.description_sale:
                result['name'] = product.name
                result['notes'] = product.description_sale
            else:
                result['name'] = product.name
        else:
            result['name'] = False
            result['notes'] = False
        return {'value': result}

project_issue_invoice()

class project_issue(osv.osv):
    _inherit = 'project.issue'

    def _check_invoice(self, cr, uid, ids, field_name, arg, context=None):
        """
        This method check if we have an invoice in issue and return True if found else False
        """
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            # check if there is an invoice in the issue
            if hasattr(issue, 'account_invoice_id') and issue.account_invoice_id.id and issue.account_invoice_id.state <> 'cancel':
                res[issue.id] = True
            else:
                res[issue.id] = False
        return res

    def _get_issue(self, cr, uid, ids, context=None):
        """
        This method trigger the store
        """
        result = {}
        proj_issue_obj = self.pool.get('project.issue')
        for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            issue_ids = proj_issue_obj.search(cr, uid, [('account_invoice_id','=',invoice.id)], context=context)
            for issue_id in issue_ids:
                result[issue_id] = True
        return result.keys()

    _columns = {
        'invoiced': fields.boolean('Invoiced', help="Indicate if the issue is invoiced or not", ),
        'issue_invoiced': fields.function(_check_invoice, method=True, string='Invoiced', type='boolean', help="Indicate if the issue has already an invoice",
                                    store = {
                                        'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['account_invoice_id'], 10),
                                        'account.invoice': (_get_issue, ['state'], 10),
                                    },),
        'account_invoice_id': fields.many2one('account.invoice', 'Account Invoice', ),
    }

    _defaults = {
        'invoiced': False,
    }

    def write(self, cr, uid, ids, values, context=None):
        """
        We cannot modify when the issue is invoiced
        """
        if not isinstance(ids, list):
            ids = [ids]

        project_issues = self.read(cr, uid, ids, ['issue_invoiced'], context=context)
        invoiced_ids = [value['id'] for value in project_issues if value['issue_invoiced']]
        if invoiced_ids:
            raise osv.except_osv(_('Error'), _('You cannot modify an invoiced issue !'))

        return super(project_issue, self).write(cr, uid, ids, values, context=context)

    def search_issue2invoice(self, cr, uid, project_ids, context=None):
        """
        This method search all issues not invoiced with project_id in selection
        """
        project_obj = self.pool.get('project.project')
        if project_ids:
            if isinstance(project_ids, (int, long,)):
                return self.search(cr, uid, [('invoiced','=',False), ('state','=','done'), ('project_id', '=', project_ids)])
            else:
                return self.search(cr, uid, [('invoiced','=',False), ('state','=','done'), ('project_id', 'in', project_ids)])
        else:
            return []

    def make_invoice(self, cr, uid, issue_ids=None, project_ids=None, use_new_cursor=False, context=None):
        if issue_ids or project_ids:
            if use_new_cursor:
                cr = pooler.get_db(use_new_cursor).cursor()
            if isinstance(issue_ids, (int, long,)):
                issue_ids = [issue_ids]
            if project_ids is None:
                project_ids = []
            project_obj = self.pool.get('project.project')
            invoice_obj = self.pool.get('account.invoice')
            invoice_line_obj = self.pool.get('account.invoice.line')
            project_issue_invoice_obj = self.pool.get('project.issue.invoice')
            product_pricelist_obj = self.pool.get('product.pricelist')
            if issue_ids:
                issue_data = self.read(cr, uid, issue_ids, ['project_id'], context=context)
                project_ids = list(set(project_ids) | set([data['project_id'][0] for data in issue_data if data['project_id']]))
            invoice_ids = []
            # Field for know the categ already invoiced
            categ_used_ids = []
            for project in project_obj.browse(cr, uid, project_ids, context=context):
                # Prepare invoice
                value_invoice = invoice_obj.onchange_partner_id(cr, uid, [], 'out_invoice', project.partner_id and project.partner_id.id)
                invoice_vals = {
                    'name': project.name,
                    'account_id': value_invoice['value']['account_id'],
                    'partner_id': project.partner_id and project.partner_id.id,
                    'address_invoice_id': value_invoice['value']['address_invoice_id'],
                    'address_contact_id': value_invoice['value']['address_contact_id'],
                    'payment_term': value_invoice['value']['payment_term'],
                    'fiscal_position': value_invoice['value']['fiscal_position'],
                    'invoice_line': [],
                }
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoice_ids.append(invoice_id)
                # Create invoice line for the lines of project issue invoice with price fixed
                invoice_issue_ids = project_issue_invoice_obj.search(cr, uid, [('project_id','=',project.id), ('price_fixed','=',True)], context=context)
                for invoice_issue in project_issue_invoice_obj.browse(cr, uid, invoice_issue_ids, context=context):
                    value = invoice_line_obj.product_id_change(
                        cr,
                        uid,
                        [],
                        invoice_issue.product_id.id,
                        uom=False,
                        partner_id=project.partner_id.id,
                        fposition_id=project.partner_id.property_account_position.id
                    )
                    pricelist_id = project.partner_id.property_product_pricelist.id
                    product_uom_id = invoice_issue.product_id.uom_id.id
                    price = product_pricelist_obj.price_get(cr, uid, [pricelist_id],
                                                            invoice_issue.product_id.id,
                                                            invoice_issue.quantity,
                                                            project.partner_id.id,
                                                            {'uom': product_uom_id,}
                                                           )[pricelist_id]
                    invoice_line_obj.create(cr, uid, {
                        'name': invoice_issue.name,
                        'invoice_id': invoice_id,
                        'account_id': value['value']['account_id'],
                        'account_analytic_id': project.analytic_account_id.id,
                        'price_unit': price,
                        'quantity': invoice_issue.quantity,
                        'uos_id': value['value']['uos_id'],
                        'invoice_line_tax_id': [(6, 0, value['value']['invoice_line_tax_id'])],
                        'product_id': invoice_issue.product_id.id,
                        'note': invoice_issue.notes,
                    }, context=context)
                # Create invoice line for the lines of project issue invoice without price fixed
                invoice_issue_ids = project_issue_invoice_obj.search(cr, uid, [('project_id','=',project.id),('price_fixed','=',False)], context=context)
                for invoice_issue_id in invoice_issue_ids:
                    # the browse change order so must be do it in for loop
                    invoice_issue = project_issue_invoice_obj.browse(cr, uid, invoice_issue_id, context=context)
                    value = invoice_line_obj.product_id_change(
                        cr,
                        uid,
                        [],
                        invoice_issue.product_id.id,
                        uom=False,
                        partner_id=project.partner_id.id,
                        fposition_id=project.partner_id.property_account_position.id
                    )
                    pricelist_id = project.partner_id.property_product_pricelist.id
                    product_uom_id = invoice_issue.product_id.uom_id.id
                    duration = 0.0
                    # If quantity > 0 then we must invoice 1 line
                    if invoice_issue.quantity > 0:
                        price = product_pricelist_obj.price_get(cr, uid, [pricelist_id],
                                                                invoice_issue.product_id.id,
                                                                invoice_issue.quantity,
                                                                project.partner_id.id,
                                                                {'uom': product_uom_id,}
                                                               )[pricelist_id]
                        invoice_line_obj.create(cr, uid, {
                            'name': invoice_issue.name,
                            'invoice_id': invoice_id,
                            'account_id': value['value']['account_id'],
                            'account_analytic_id': project.analytic_account_id.id,
                            'price_unit': price,
                            'quantity': invoice_issue.quantity,
                            'uos_id': value['value']['uos_id'],
                            'invoice_line_tax_id': [(6, 0, value['value']['invoice_line_tax_id'])],
                            'product_id': invoice_issue.product_id.id,
                            'note': invoice_issue.notes,
                        }, context=context)
                        duration -= invoice_issue.quantity
                    if invoice_issue.categ_id and invoice_issue.categ_id.id:
                        categ_used_ids.append(invoice_issue.categ_id.id)
                        issue_categ_ids = self.search(cr, uid, [('project_id','=',project.id), ('categ_id','=',invoice_issue.categ_id.id), ('id', 'in', issue_ids)], context=context)
                        self.write(cr, uid, issue_categ_ids, {'account_invoice_id': invoice_id, 'invoiced': True}, context=context)
                    elif categ_used_ids:
                        issue_categ_ids = self.search(cr, uid, [('project_id','=',project.id), ('categ_id','not in',categ_used_ids), ('id', 'in', issue_ids)], context=context)
                        self.write(cr, uid, issue_categ_ids, {'account_invoice_id': invoice_id, 'invoiced': True}, context=context)
                    else:
                        issue_categ_ids = self.search(cr, uid, [('project_id','=',project.id), ('id', 'in', issue_ids)], context=context)
                        self.write(cr, uid, issue_categ_ids, {'account_invoice_id': invoice_id, 'invoiced': True}, context=context)
                    for issue_categ in self.browse(cr, uid, issue_categ_ids, context=context):
                        duration += issue_categ.duration_timesheet
                    # If duration > 0, the duration of all tickets not invoiced for this category is more than the quantity indicate in project issue invoice so invoice the difference.
                    if duration > 0:
                        price = product_pricelist_obj.price_get(cr, uid, [pricelist_id],
                                                                invoice_issue.product_id.id,
                                                                duration,
                                                                project.partner_id.id,
                                                                {'uom': product_uom_id,}
                                                               )[pricelist_id]
                        invoice_line_obj.create(cr, uid, {
                            'name': invoice_issue.name,
                            'invoice_id': invoice_id,
                            'account_id': value['value']['account_id'],
                            'account_analytic_id': project.analytic_account_id.id,
                            'price_unit': price,
                            'quantity': duration,
                            'uos_id': value['value']['uos_id'],
                            'invoice_line_tax_id': [(6, 0, value['value']['invoice_line_tax_id'])],
                            'product_id': invoice_issue.product_id.id,
                            'note': invoice_issue.notes,
                        }, context=context)

            # Compute the amount of invoice
            if invoice_ids:
                invoice_obj.button_compute(cr, uid, invoice_ids, context)
            if use_new_cursor:
                cr.commit()
                cr.close()
            return invoice_ids
        else:
            return False

    def case_close(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """

        res = super(project_issue, self).case_close(cr, uid, ids, *args)
        for issue in self.browse(cr, uid, ids):
            if issue.project_id.invoice_issue_policy == 'auto':
                invoice = self.make_invoice(cr, uid, issue.id, context=None)
                if invoice:
                    message = _("Issue '%s' has been invoiced.") % issue.name
                    self.log(cr, uid, issue.id, message)
        return res

    def run_scheduler(self, cr, uid, use_new_cursor=False, context=None):
        ''' Runs through scheduler.
        @param use_new_cursor: False or the dbname
        '''
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        project_ids = self.pool.get('project.project').search(cr, uid, [('invoice_issue_policy','=','manual'),('state','=','open')], context=context)
        issue_ids = self.search_issue2invoice(cr, uid, project_ids, context=context)
        # Search all project with lines with price fixed
        issue_inv_obj = self.pool.get('project.issue.invoice')
        issue_inv_ids = issue_inv_obj.search(cr, uid, [('project_id', 'in', project_ids),('quantity', '>', 0.0)], context=context)
        issue_inv_data = issue_inv_obj.read(cr, uid, issue_inv_ids, ['project_id'], context=context)
        project_ids = list(set([data['project_id'][0] for data in issue_inv_data if data['project_id']]))
        if issue_ids or project_ids:
            self.make_invoice(cr, uid, issue_ids, project_ids, use_new_cursor=use_new_cursor, context=None)
        if use_new_cursor:
            cr.commit()
            cr.close()

project_issue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
