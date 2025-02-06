# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class CemeteryLocation(models.Model):
    _name = "cemetery.location"
    _description = "Cemetery Location"

    cemetery_id = fields.Many2one("cemetery")
    parent_id = fields.Many2one("cemetery.location")
    location_cemetery_id = fields.Many2one(
        "stock.location", required=True, ondelete="cascade", delegate=True
    )
    partner_id = fields.Many2one("res.partner")
    beneficiary_ids = fields.One2many("cemetery.beneficiary", "cemetery_location_id")
    available_space = fields.Integer(compute="_compute_available_space")
    occupied_space = fields.Integer(compute="_compute_available_space")

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if self._context.get("is_cemetery_location_kanban"):
            domain += [("usage", "!=", "view")]
        return super()._search(domain, offset, limit, order, access_rights_uid)

    def _compute_available_space(self):
        stock_quant_obj = self.env["stock.quant"]
        for location in self:
            storage_cap2 = location.location_cemetery_id
            stock_quant = stock_quant_obj.search(
                [
                    ("location_id", "=", location.location_cemetery_id.id),
                    ("lot_id", "!=", False),
                ]
            )
            stock_count = sum(stock_quant.mapped("quantity"))
            storage_cap = stock_quant.mapped(
                "storage_category_id.product_capacity_ids"
            ).filtered(lambda l: l.product_id.id in stock_quant.product_id.ids)
            available_space = 0
            occupied_space = 0
            if stock_quant.location_id.location_id.usage == "view":
                available_space = stock_count
                occupied_space = storage_cap.quantity - stock_count
            else:
                available_space = storage_cap.quantity - stock_count
                occupied_space = stock_count

            location.available_space = available_space
            location.occupied_space = occupied_space
