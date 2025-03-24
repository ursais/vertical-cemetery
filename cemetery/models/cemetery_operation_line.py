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
    beneficiary_id = fields.Many2one('cemetery.beneficiary')
    beneficiary_type = fields.Selection(selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")], required=True, default="rights_holder")
    cemetery_location_id = fields.Many2one('cemetery.location', string='Location', required=True)
    death_date = fields.Datetime(string="Death Date")
    is_confirmed = fields.Boolean(default=False)

    # Link to stock operations
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    move_id = fields.Many2one('stock.move', string='Stock Move')

    # State of each line
    state = fields.Selection([('draft', 'Draft'), ('reserved', 'Reserved'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], compute='_compute_state', store=True)

    @api.depends('move_id.state', 'is_confirmed')
    def _compute_state(self):
        for line in self:
            if line.is_confirmed:
                line.state = 'confirmed'
            elif line.move_id and line.move_id.state == 'assigned':
                line.state = 'reserved'
            elif line.move_id and line.move_id.state == 'cancel':
                line.state = 'cancelled'
            else:
                line.state = 'draft'

    def action_reserve(self):
        """Create or assign stock picking and reserve the spot"""
        for line in self:

            # Assign the beneficiary
            line.beneficiary_id = line.partner_id.beneficiary_id.id

            # Skip if already reserved or confirmed
            if line.state in ['reserved', 'confirmed']:
                continue

            # Get the cemetery product
            cemetery_product = line.env.company.cemetery_product_template.product_variant_id
            if not cemetery_product:
                raise ValidationError(_("Please configure a cemetery product in the settings"))

            # Check if operation already has a picking
            picking = line.operation_id.picking_id
            if not picking:
                # Create a new picking for this operation
                picking_type = line.env['stock.picking.type'].search([
                    ('code', '=', 'internal'),
                    ('company_id', '=', line.env.company.id)
                ], limit=1)

                if not picking_type:
                    raise ValidationError(_("No internal transfer operation type found"))

                # Get reservation location
                reservation_location_id = line._get_reservation_location()

                picking_vals = {
                    'name': f'CEMETERY/{line.operation_id.name}',
                    'picking_type_id': picking_type.id,
                    'location_id': reservation_location_id,
                    'location_dest_id': line.cemetery_location_id.location_cemetery_id.id,
                    'scheduled_date': fields.Datetime.now(),
                    'origin': line.operation_id.name,
                    'company_id': line.env.company.id,
                    'move_type': 'direct',
                }

                picking = line.env['stock.picking'].create(picking_vals)
                line.operation_id.picking_id = picking

            # Set the picking_id on the op. line
            line.picking_id = picking.id

            # Create move for this line
            if not line.move_id:

                # Get the locations directly from the picking to ensure consistency
                src_location_id = picking.location_id.id
                dest_location_id = picking.location_dest_id.id

                move_vals = {
                    'company_id': line.env.company.id,
                    'date': datetime.datetime.now(),
                    'location_id': src_location_id,
                    'location_dest_id': dest_location_id,
                    'name': f'Reservation: {line.partner_id.name or "New"}',
                    'picking_id': picking.id,
                    'product_id': cemetery_product.id,
                    'product_uom': cemetery_product.uom_id.id,
                    'product_uom_qty': 1,
                    'state': 'draft',
                    'cemetery_operation_line_id': line.id,
                }

                move = line.env['stock.move'].create(move_vals)
                line.move_id = move.id

                # Create move lines if the beneficiary already has a serial
                if move and line.beneficiary_id and line.beneficiary_id.serial_id:

                    quant = line.env["stock.quant"].search([
                        ("location_id", "=", src_location_id),
                        ("lot_id", "=", line.beneficiary_id.serial_id.id)
                    ], limit=1)

                    if quant:
                        move_line_vals = {
                            'move_id': move.id,
                            'quant_id': quant.id,
                            'product_id': cemetery_product.id,
                            'product_uom_id': cemetery_product.uom_id.id,
                            'location_id': src_location_id,
                            'location_dest_id': dest_location_id,
                            'lot_id': line.beneficiary_id.serial_id.id,
                            # 'quantity': 0,  # Will be set when confirming
                        }

                        move_line = line.env['stock.move.line'].create(move_line_vals)

                        move.move_line_ids = [(6, 0, [move_line])]


            # Confirm the picking if not already
            if picking.state == 'draft':
                picking.action_confirm()

            # Try to assign (reserve) the move
            if line.move_id.state not in ['assigned', 'done']:
                line.move_id._action_assign()

    def action_confirm(self):
        """Confirm this line's reservation (mark as deceased)"""
        for line in self:
            # Skip if already confirmed or not reserved
            if line.state == 'confirmed' or line.state != 'reserved':
                continue

            # For deceased beneficiaries, ensure death date is set
            if line.beneficiary_type == 'deceased' and not line.death_date:
                raise ValidationError(_("Death date must be set for deceased beneficiaries"))

            # Create or update beneficiary
            if not line.beneficiary_id:
                line._create_beneficiary()
            # else:
                # Update death date on existing beneficiary
                # line.beneficiary_id.write({
                #     'death_date': line.death_date,
                # })

            # Process just this move to done
            if line.move_id and line.move_id.state == 'assigned':
                # Set done quantity
                for move_line in line.move_id.move_line_ids:
                    move_line.quantity = move_line.reserved_qty

                # Process the move
                line.move_id._action_done()
                line.is_confirmed = True

    def action_cancel(self):
        """Cancel this line's reservation"""
        for line in self:
            # Skip if already confirmed
            if line.state == 'confirmed':
                continue

            # Cancel the move
            if line.move_id and line.move_id.state != 'done':
                line.move_id._action_cancel()

    def _get_reservation_location(self):
        """Get the stock.location record for reservations"""
        cemetery_location = self.env['cemetery.location'].search([
            ('usage', '=', 'internal'),
            ('is_reserve_location', '=', True),
            ('cemetery_id', '=', self.cemetery_location_id.cemetery_id.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not cemetery_location:
            raise ValidationError(_("No reservation location found for this Cemetery"))

        # Get the actual stock.location ID associated with this cemetery location
        stock_location = cemetery_location.location_cemetery_id

        if not stock_location:
            raise ValidationError(_("Cemetery location doesn't have an associated stock location"))

        return stock_location.id  # Return the ID, not the record

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """When partner is selected, populate fields from partner"""
        if self.partner_id:

            # Check if partner already has a beneficiary record
            if self.partner_id.beneficiary_id:
                self.beneficiary_id = self.partner_id.beneficiary_id
                self.beneficiary_type = self.partner_id.cemetery_beneficiary_type or 'rights_holder'

                # # If it's a deceased beneficiary, set death date
                # if self.beneficiary_type == 'deceased' and self.beneficiary_id.death_date:
                #     self.death_date = self.beneficiary_id.death_date

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

        # Then create the beneficiary
        vals = {
            'name': self.name,
            'partner_id': partner.id,
            'serial_number': f'{self.operation_id.name}-{self.id}',
            'beneficiary_type': self.beneficiary_type,
            'death_date': self.death_date,
            'cemetery_location_id': self.cemetery_location_id.id,
        }

        beneficiary = self.env['cemetery.beneficiary'].create(vals)
        self.beneficiary_id = beneficiary.id

        # Update the partner record with link to beneficiary
        partner.write({
            'beneficiary_id': beneficiary.id,
        })

        return beneficiary
