# cemetery/models/cemetery_operation.py
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CemeteryOperation(models.Model):
    _name = "cemetery.operation"
    _description = "Cemetery Operation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, copy=False, default=lambda self: _('New'))
    date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'), ('reserved', 'Reserved'), ('partially_confirmed', 'Partially Confirmed'), ('confirmed', 'Fully Confirmed'), ('cancelled', 'Cancelled')], default='draft', tracking=True, store=True)

    # Link to stock picking
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')

    cemetery_id = fields.Many2one('cemetery', required=True)
    operation_line_ids = fields.One2many('cemetery.operation.line', 'operation_id', string='Beneficiaries')


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cemetery.operation') or _('New')
        return super().create(vals_list)

    def action_reserve(self):
        """Reserve all lines in the operation"""
        for operation in self:
            if not operation.operation_line_ids:
                raise ValidationError(_("No beneficiaries were added to this operation"))

            # Have each line create its reservation
            for line in operation.operation_line_ids:
                line.action_reserve()

    def action_confirm_deceased(self):
        """Confirm only deceased beneficiaries"""
        self.ensure_one()
        deceased_lines = self.operation_line_ids.filtered(
            lambda l: l.beneficiary_type == 'deceased' and l.death_date and not l.is_confirmed
        )

        if not deceased_lines:
            raise ValidationError(_("No new deceased beneficiaries to confirm"))

        for line in deceased_lines:
            line._confirm_reservation()

        # The state will be computed automatically

    def action_cancel(self):
        self.ensure_one()
        # Only cancel unconfirmed lines
        for line in self.operation_line_ids.filtered(lambda l: not l.is_confirmed):
            if line.reservation_move_id and line.reservation_move_id.state != 'done':
                line.reservation_move_id.action_cancel()

        self.state = 'cancelled'
