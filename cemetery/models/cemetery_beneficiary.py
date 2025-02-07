# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class CemeteryBeneficiary(models.Model):
    _name = "cemetery.beneficiary"
    _rec_name = "partner_id"
    _description = "Cemetery Beneficiary"

    partner_id = fields.Many2one("res.partner")
    serial_id = fields.Many2one("stock.lot")
    beneficiary_type = fields.Selection(
        selection=[("deceased", "Deceased"), ("rightsholder", "Rightsholder")],
        string="Beneficiary type",
    )
    death_date = fields.Datetime(string="Death Date")
    last_movement_date = fields.Datetime(string="Last Movement Date")
    cemetery_location_id = fields.Many2one("cemetery.location", string="Souce Location")
    dest_cemetery_location_id = fields.Many2one(
        "cemetery.location", string="Destination Location"
    )

    @api.model
    def create(self, vals_list):
        beneficiary = super().create(vals_list)
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
        beneficiary.serial_id.beneficiary_id = beneficiary.id
        stock_move_list.append(
            {
                "company_id": self.env.company.id,
                "product_id": cemetery_product.id,
                "product_uom": cemetery_product.uom_id.id,
                "location_id": inventory_loss.id,
                "location_dest_id": beneficiary.cemetery_location_id.location_cemetery_id.id,
                "name": beneficiary.beneficiary_type,
                "procure_method": "make_to_stock",
                "product_uom_qty": 1,
                "date": beneficiary.death_date,
                "is_inventory": True,
                "picked": True,
                "state": "confirmed",
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": inventory_loss.id,
                            "location_dest_id": beneficiary.cemetery_location_id.location_cemetery_id.id,
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
        stock_move = StockMove.create(stock_move_list)
        stock_move._action_done()
        return beneficiary
