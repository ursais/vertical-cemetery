# cemetery/models/cemetery_operation_line.py
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CemeteryOperationLine(models.Model):
    _name = "cemetery.operation.line"
    _description = "Cemetery Operation Line"

    operation_id = fields.Many2one('cemetery.operation', required=True, ondelete='cascade')

    # Link to existing partner if already exists
    partner_id = fields.Many2one('res.partner', string='Contact')
    beneficiary_id = fields.Many2one('cemetery.beneficiary', compute="_compute_beneficiary_id")
    beneficiary_type = fields.Selection(selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")], related="beneficiary_id.beneficiary_type")
    cemetery_location_id = fields.Many2one('cemetery.location', string='Location', required=True, related="operation_id.cemetery_location_id")
    is_confirmed = fields.Boolean(default=False)
    is_reserved = fields.Boolean(default=False)
    picking_id = fields.Many2one("stock.picking")

    # State of each line
    state = fields.Selection([('draft', 'Draft'), ('reserved', 'Reserved'), ('confirmed', 'Confirmed')], compute='_compute_state', store=True)

    @api.depends('is_confirmed')
    def _compute_state(self):
        for line in self:
            if line.is_confirmed:
                line.state = 'confirmed'
            elif line.is_reserved:
                line.state = 'reserved'
            else:
                line.state = 'draft'


    def action_confirm(self):
        """Confirm this line's reservation (mark as deceased)"""
        for line in self:

            line.picking_id.button_validate()

            line.beneficiary_id.write(
                    {
                        "cemetery_location_id": line.cemetery_location_id.id,
                        "occupation_date": datetime.date.today(),
                        "beneficiary_type": "deceased",
                    }, "operation",
                )

            line.is_confirmed = True
            line.operation_id.state = "partially_confirmed"
            line.operation_id.check_completion()


    def action_reserve(self):
        main_location = self.env["cemetery.location"].search(
            [
                ("cemetery_id", "=", self.cemetery_location_id.cemetery_id.id),
                ("is_reserve_location", "=", True),
                ("parent_id", "=", False),
                ("location_cemetery_id.usage", "!=", "view"),
                ("location_cemetery_id.location_id.usage", "=", "view"),
            ], limit=1,
        ).location_cemetery_id

        for line in self:
            # Skip if already confirmed or not reserved
            if line.state == 'confirmed':
                continue

            # Create or update beneficiary
            if not line.beneficiary_id:
                line._create_beneficiary()

            # Create picking and move in draft state
            StockMove = self.env["stock.move"]
            old_cemetery_location_id = line.beneficiary_id.cemetery_location_id.location_cemetery_id
            picking = self.env["stock.picking"].create(
                {
                    "partner_id": line.partner_id.id,
                    "picking_type_id": line.cemetery_location_id.location_cemetery_id.warehouse_id.int_type_id.id,
                    "location_id": main_location.id,
                    "location_dest_id": line.cemetery_location_id.location_cemetery_id.id,
                    "is_cemetery": True,
                }
            )
            stock_move_list = line.beneficiary_id.with_context(
                source_location=old_cemetery_location_id.id,
                desti_location_id=line.cemetery_location_id.location_cemetery_id.id,
                picking_id=picking.id,
                is_cemetery=True,
                date=datetime.date.today()
            )._prepare_stock_move_vals(line.beneficiary_id)
            StockMove.create(stock_move_list)
            picking.action_confirm()
            picking.action_assign()
            line.picking_id = picking.id
            line.state = "reserved"
            line.operation_id.state = "reserved"


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """When partner is selected, populate fields from partner"""
        if self.partner_id:

            # Check if partner already has a beneficiary record
            if self.partner_id.beneficiary_id:
                self.beneficiary_id = self.partner_id.beneficiary_id
                self.beneficiary_type = self.partner_id.cemetery_beneficiary_type or 'rights_holder'


    def _get_or_create_partner(self):
        """Get existing partner or create a new one"""
        if self.partner_id:
            return self.partner_id

        # Create new partner
        partner_vals = {
            'name': self.name,
            'is_cemetery_beneficiary': True,
            'cemetery_beneficiary_type': self.beneficiary_type,
        }

        partner = self.env['res.partner'].create(partner_vals)
        self.partner_id = partner.id
        return partner

    def _create_beneficiary(self):
        """Create a beneficiary record based on the operation line"""
        # First ensure we have a partner
        partner = self._get_or_create_partner()

        main_location = self.env["cemetery.location"].search(
            [
                ("cemetery_id", "=", self.operation_id.cemetery_id.id),
                ("is_reserve_location", "=", True),
                ("parent_id", "=", False),
                ("location_cemetery_id.usage", "!=", "view"),
                ("location_cemetery_id.location_id.usage", "=", "view"),
            ], limit=1,
        )
        # Then create the beneficiary
        vals = {
            'name': partner.name,
            'partner_id': partner.id,
            'serial_number': f'{self.operation_id.name}-{self.id}',
            'beneficiary_type': self.beneficiary_type,
            'cemetery_location_id': main_location.id,
        }

        beneficiary = self.env['cemetery.beneficiary'].create(vals)
        self.beneficiary_id = beneficiary.id

        # Update the partner record with link to beneficiary
        partner.write({
            'beneficiary_id': beneficiary.id,
        })

        return beneficiary

    @api.depends("partner_id")
    def _compute_beneficiary_id(self):
        for record in self:
            if record.partner_id.beneficiary_id:
                record.beneficiary_id = record.partner_id.beneficiary_id.id
            else:
                record.beneficiary_id = False