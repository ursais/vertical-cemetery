# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class CemeteryBeneficiary(models.Model):
    _name = "cemetery.beneficiary"
    _description = "Cemetery Beneficiary"

    name = fields.Char()
    # address fields
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    country_code = fields.Char(related="country_id.code", string="Country Code")
    # BackendField-Used for Storing a Partner Value
    partner_id = fields.Many2one("res.partner", string="Name")

    serial_number = fields.Char(string="Serial Number")
    # BackendField-Used for Storing a Serial Number Value
    serial_id = fields.Many2one("stock.lot")

    beneficiary_type = fields.Selection(
        selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")],
        string="Beneficiary type",
    )
    death_date = fields.Datetime(string="Death Date")
    cemetery_location_id = fields.Many2one(
        "cemetery.location", string="Current Location"
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
                "date": beneficiary.death_date,
                "is_inventory": True,
                "picked": True,
                "state": "confirmed",
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
                            "date": beneficiary.death_date,
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
        StockMove = self.env["stock.move"]
        stock_move_list = []
        cemetery_product = (
            self.env.company.cemetery_product_template
            and self.env.company.cemetery_product_template.product_variant_id
            or self.env["product.product"]
        )
        partner_id = self.env["res.partner"].create(
            {
                "name": beneficiary.name,
                "street": beneficiary.street,
                "street2": beneficiary.street2,
                "city": beneficiary.city,
                "state_id": beneficiary.state_id.id,
                "zip": beneficiary.zip,
                "country_id": beneficiary.country_id.id,
                "is_cemetery_beneficiary": True,
                "cemetery_beneficiary_type": beneficiary.beneficiary_type,
            }
        )
        beneficiary.partner_id = partner_id.id
        beneficiary.partner_id.beneficiary_id = beneficiary.id
        serial_id = self.env["stock.lot"].create(
            {
                "name": beneficiary.serial_number,
                "product_id": cemetery_product.id,
                "is_cemetery_beneficiary": True,
            }
        )
        beneficiary.serial_id = serial_id.id
        beneficiary.serial_id.beneficiary_id = beneficiary.id
        stock_move_list = self._prepare_stock_move_vals(beneficiary)
        stock_move = StockMove.create(stock_move_list)
        stock_move._action_done()
        return beneficiary

    def write(self, vals):
        old_cemetery_location_id = self.cemetery_location_id.location_cemetery_id
        result = super().write(vals)
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
                    "location_id": old_cemetery_location_id.id,
                    "location_dest_id": new_location.location_cemetery_id.id,
                }
            )
            stock_move_list = self.with_context(
                source_location=old_cemetery_location_id.id,
                desti_location_id=new_location.location_cemetery_id.id,
                picking_id=picking.id,
            )._prepare_stock_move_vals(self)
            stock_move = StockMove.create(stock_move_list)
            picking.action_confirm()
            picking.action_assign()
            stock_move._action_done()
        return result
