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

    @api.model_create_multi
    def create(self, vals_list):
        beneficiary = super().create(vals_list)
        StockMove = self.env["stock.move"]
        stock_move_list = []
        # inventory  beneficiary
        inventory_loss = self.env["stock.location"].search(
            [
                ("usage", "=", "inventory"),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        StockPickingType = self.env["stock.picking.type"]
        for data in beneficiary:
            picking_id = StockPickingType.search(
                [
                    (
                        "warehouse_id",
                        "=",
                        data.cemetery_location_id.cemetery_id.warehouse_id.id,
                    ),
                    ("code", "=", "internal"),
                ]
            )
            internal_picking = self.env["stock.picking"].create(
                {
                    "partner_id": data.partner_id.id,
                    "picking_type_id": picking_id.id,
                    "location_id": data.cemetery_location_id.location_cemetery_id.id,
                    "location_dest_id": data.dest_cemetery_location_id.location_cemetery_id.id,
                    "state": "draft",
                }
            )
            stock_move_list.append(
                {
                    "company_id": self.env.company.id,
                    "product_id": self.env.company.cemetery_product_template.product_variant_ids
                    and self.env.company.cemetery_product_template.product_variant_ids.ids[
                        0
                    ],
                    "product_uom": data.serial_id.product_id.uom_id.id,
                    "picking_id": internal_picking.id,
                    "location_id": internal_picking.location_id.id,
                    "location_dest_id": internal_picking.location_dest_id.id,
                    "name": data.beneficiary_type,
                    "procure_method": "make_to_stock",
                    "product_uom_qty": 1,
                    "date": data.death_date,
                    "state": "draft",
                    "move_line_ids": [
                        (
                            0,
                            0,
                            {
                                "location_id": internal_picking.location_id.id,
                                "location_dest_id": internal_picking.location_dest_id.id,
                                "product_id": self.env.company.cemetery_product_template.product_variant_ids
                                and self.env.company.cemetery_product_template.product_variant_ids.ids[
                                    0
                                ],
                                "product_uom_id": data.serial_id.product_id.uom_id.id,
                                "company_id": self.env.company.id,
                                "date": data.death_date,
                                "lot_id": data.serial_id.id,
                                "quantity": 1,
                            },
                        )
                    ],
                }
            )
            data.serial_id.beneficiary_id = data.id
        StockMove.create(stock_move_list)
        return beneficiary
