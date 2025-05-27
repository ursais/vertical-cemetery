# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CemeteryBeneficiary(models.Model):
    _name = "cemetery.beneficiary"
    _description = "Cemetery Beneficiary"

    name = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Name")

    serial_number = fields.Char(string="Serial Number")
    # BackendField-Used for Storing a Serial Number Value
    serial_id = fields.Many2one("stock.lot")

    beneficiary_type = fields.Selection(
        selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")],
        string="Beneficiary type",
        required=True,
    )
    occupation_date = fields.Datetime(string="Occupation Date")
    cemetery_location_id = fields.Many2one(
        "cemetery.location", string="Current Location"
    )
    complete_name = fields.Char()

    @api.constrains("cemetery_location_id")
    def _check_cemetery_location_id(self):
        stock_quant_obj = self.env["stock.quant"]
        occupied_space = 0
        cemetery_product = (
            self.env.company.cemetery_product_template
            and self.env.company.cemetery_product_template.product_variant_id
            or self.env["product.product"]
        )
        for rec in self:
            if rec.cemetery_location_id:
                location = rec.cemetery_location_id.location_cemetery_id
                occupied_space += sum(
                    stock_quant_obj.search([("location_id", "=", location.id)]).mapped(
                        "quantity"
                    )
                )
                storage_cap = location.storage_category_id.mapped(
                    "product_capacity_ids"
                ).filtered(lambda l: l.product_id.id == cemetery_product.id)
                available_space = storage_cap.quantity
                if occupied_space >= available_space:
                    raise ValidationError(
                        _(
                            f"Please choose a different location, as this {rec.cemetery_location_id.display_name} one is fully occupied."
                        )
                    )

    def _prepare_stock_move_vals(self, beneficiary):
        StockMove = self.env["stock.move"]
        StockQuant = self.env["stock.quant"]
        stock_move_list = []
        cemetery_product = (
            self.env.company.cemetery_product_template
            and self.env.company.cemetery_product_template.product_variant_id
            or self.env["product.product"]
        )
        inventory_loss = self.env["stock.location"].search(
            [
                ("usage", "=", "inventory"),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        location_id = inventory_loss.id
        location_dest_id = beneficiary.cemetery_location_id.location_cemetery_id.id
        if self._context.get("source_location") and self._context.get(
            "desti_location_id"
        ):
            location_id = self._context.get("source_location")
            location_dest_id = self._context.get("desti_location_id")
        beneficiary.complete_name = (
            self.env["stock.location"].browse(location_dest_id).complete_name
        )
        stock_move_list.append(
            {
                "company_id": self.env.company.id,
                "product_id": cemetery_product.id,
                "product_uom": cemetery_product.uom_id.id,
                "location_id": location_id,
                "location_dest_id": location_dest_id,
                "name": beneficiary.beneficiary_type,
                "procure_method": "make_to_stock",
                "product_uom_qty": 1,
                "date": beneficiary.occupation_date,
                "is_inventory": True,
                "picked": True,
                "state": "confirmed",
                "is_cemetery": True,
                "picking_id": self._context.get("picking_id")
                              or self.env["stock.picking"],
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": location_id,
                            "location_dest_id": location_dest_id,
                            "product_id": cemetery_product.id,
                            "product_uom_id": cemetery_product.uom_id.id,
                            "company_id": self.env.company.id,
                            "date": beneficiary.occupation_date,
                            "lot_id": beneficiary.serial_id.id,
                            "quantity": 1,
                        },
                    )
                ],
            }
        )
        return stock_move_list

    @api.model
    def create(self, vals_list):
        beneficiary = super().create(vals_list)

        cemetery_product = (
            self.env.company.cemetery_product_template
            and self.env.company.cemetery_product_template.product_variant_id
            or self.env["product.product"]
        )

        # Generate a serial number
        beneficiary.serial_number = beneficiary.name

        # 1. Create the lot
        serial_id = self.env["stock.lot"].create({
            "name": beneficiary.serial_number,
            "beneficiary_id": beneficiary.id,
            'location_id': beneficiary.cemetery_location_id.location_cemetery_id.id,
            "product_id": cemetery_product.id,
            "is_cemetery_beneficiary": True,
        })

        main_location = self.env["cemetery.location"].search(
            [
                ("is_reserve_location", "=", True),
                ("parent_id", "=", False),
                ("location_cemetery_id.usage", "!=", "view"),
                ("location_cemetery_id.location_id.usage", "=", "view"),
            ], limit=1,
        ).location_cemetery_id

        #2 Create the quant
        quant = self.env['stock.quant'].create({
            'lot_id': serial_id.id,
            'location_id': serial_id.location_id.id or main_location.id,
            'product_id': cemetery_product.id,
            'inventory_quantity': 1.0,
            'quantity': 0.0,  # Initial quantity is 0
            'is_cemetery': True,
        })

        #3 Apply the inventory to make it available
        quant.action_apply_inventory()

        # Update the beneficiary with the serial
        beneficiary.serial_id = serial_id.id
        serial_id.beneficiary_id = beneficiary.id

        # # Now the lot exists in the reserve location and can be moved later
        # if beneficiary.cemetery_location_id:
        #     StockMove = self.env["stock.move"]
        #     stock_move_list = self._prepare_stock_move_vals(beneficiary)
        #     stock_move = StockMove.create(stock_move_list)
        #     stock_move._action_done()

        return beneficiary

    @api.model
    def write(self, vals):
        old_cemetery_location_id = self.cemetery_location_id.location_cemetery_id
        inventory_loss = self.env["stock.location"].search(
            [
                ("usage", "=", "inventory"),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        result = super().write(vals)
        if self.cemetery_location_id:
            StockMove = self.env["stock.move"]
            if (
                "cemetery_location_id" in vals
                and vals.get("cemetery_location_id", False) != old_cemetery_location_id.id
            ):
                new_location = self.env["cemetery.location"].search(
                    [("id", "=", vals.get("cemetery_location_id"))]
                )
                picking = self.env["stock.picking"].create(
                    {
                        "partner_id": self.partner_id.id,
                        "picking_type_id": self.cemetery_location_id.location_cemetery_id.warehouse_id.int_type_id.id,
                        "location_id": old_cemetery_location_id.id or inventory_loss.id,
                        "location_dest_id": new_location.location_cemetery_id.id,
                        "is_cemetery": True,
                    }
                )
                stock_move_list = self.with_context(
                    source_location=old_cemetery_location_id.id,
                    desti_location_id=new_location.location_cemetery_id.id,
                    picking_id=picking.id,
                    is_cemetery=True
                )._prepare_stock_move_vals(self)
                stock_move = StockMove.create(stock_move_list)
                picking.action_confirm()
                picking.action_assign()
                stock_move._action_done()
        return result

    def action_open_partner(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_partner_form")
        action['domain'] = [('id', '=', self.partner_id.id)]
        action['context'] = {
            'default_id': self.partner_id.id,  # Set default partner id in the context
            'form_view_ref': 'base.view_partner_form',  # Reference to the partner form view
        }
        return action
