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

class project_issue_invoice(osv.osv):
    _name = 'project.issue.invoice'
    _description = 'Invoice Project Issue'
    _order = 'sequence, id'

    _columns = {
        'invoice_id': fields.many2one('project.project', 'Project Reference', required=True, select=True, readonly=True),
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

    _columns = {
        'invoiced': fields.boolean('Invoiced', help="Indicate if the issue is invoiced or not"),
    }

    _defaults = {
        'invoiced': False,
    }

project_issue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
