# cemetery/models/cemetery_operation.py
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CemeteryOperation(models.Model):
    _name = "cemetery.operation"
    _description = "Cemetery Operation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, copy=False, default=lambda self: _('New'))
    date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'), ('reserved', 'Reserved'), ('partially_confirmed', 'Partially Confirmed'), ('confirmed', 'Fully Confirmed')], default='draft', tracking=True, store=True)

    # Link to stock picking
    # picking_id = fields.Many2one('stock.picking', string='Stock Picking')

    cemetery_id = fields.Many2one('cemetery', required=True)
    operation_line_ids = fields.One2many('cemetery.operation.line', 'operation_id', string='Beneficiaries')

    cemetery_location_id = fields.Many2one("cemetery.location", string='Location', required=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cemetery.operation') or _('New')
        return super().create(vals_list)


    def check_completion(self):
        for operation in self:
            for line in operation.operation_line_ids:
                if line.state != "confirmed":
                    operation.state = "partially_confirmed"
                    break
                else:
                    operation.state = "confirmed"
