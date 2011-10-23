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

import threading
from osv import osv


class invoice_issue(osv.osv_memory):
    _name = 'invoice.issue'
    _description = 'Invoice Issue'

    def _invoice_issue_calculation_all(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        proj_issue_obj = self.pool.get('project.issue')
        proj_issue_obj.run_scheduler(cr, uid, use_new_cursor=cr.dbname, context=context)
        return {}

    def invoice_issue_calculation(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        threaded_calculation = threading.Thread(target=self._invoice_issue_calculation_all, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}

invoice_issue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
