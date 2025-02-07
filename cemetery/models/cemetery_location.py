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
    available_space = fields.Integer(compute="_compute_available_occupied_space")
    occupied_space = fields.Integer(compute="_compute_available_occupied_space")

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if self._context.get("is_cemetery_location_kanban"):
            domain += [("usage", "!=", "view")]
        return super()._search(domain, offset, limit, order, access_rights_uid)

    def _compute_available_occupied_space(self):
        stock_quant_obj = self.env["stock.quant"]
        available_space = 0
        occupied_space = 0
        for cem_location in self:
            location = cem_location.location_cemetery_id
            cemetery_product = (
                self.env.company.cemetery_product_template
                and self.env.company.cemetery_product_template.product_variant_id
                or self.env["product.product"]
            )
            storage_cap = location.storage_category_id.mapped(
                "product_capacity_ids"
            ).filtered(lambda l: l.product_id.id == cemetery_product.id)
            available_space = storage_cap.quantity
            occupied_space = sum(
                stock_quant_obj.search([("location_id", "=", location.id)]).mapped(
                    "quantity"
                )
            )
            cem_location.available_space = available_space - occupied_space
            cem_location.occupied_space = occupied_space
