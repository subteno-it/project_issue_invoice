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

from openerp import models, fields


class ProjectProject(models.Model):
    _inherit = 'project.project'

    invoice_issue_ids = fields.One2many('project.issue.invoice', 'project_id', string='Invoice Project Issue', help='Set method to invoice the issues closed')
    invoice_issue_policy = fields.Selection([
        ('none', 'None'),
        ('auto', 'Auto'),
        ('manual', 'Manual')], string='Invoice Issue Policy', default='none', help="""If the issue change state to done and must be create a draft invoice per issue, set to 'Auto Invoice',\n
If invoice any issues done, set to 'manuel', create one draft invoice for all issues done not invoiced""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
