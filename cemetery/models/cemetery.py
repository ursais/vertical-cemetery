# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class Cemetery(models.Model):
    _name = "cemetery"
    _description = "Cemetery"

    warehouse_id = fields.Many2one(
        "stock.warehouse", "Warehouse", required=True, ondelete="cascade", delegate=True
    )
    available_space = fields.Integer(compute="_compute_available_occupied_space")
    occupied_space = fields.Integer(compute="_compute_available_occupied_space")

    def _compute_available_occupied_space(self):
        stock_quant_obj = self.env["stock.quant"]
        cemetery_product = (
            self.env.company.cemetery_product_template
            and self.env.company.cemetery_product_template.product_variant_id
            or self.env["product.product"]
        )
        CemeteryLocation = self.env["cemetery.location"]
        for cemetery in self:
            available_space = 0
            occupied_space = 0
            cemetery_locations = CemeteryLocation.search(
                [("cemetery_id", "=", cemetery.id), ("usage", "!=", "view")]
            )
            for cem_location in cemetery_locations:
                location = cem_location.location_cemetery_id
                storage_cap = location.storage_category_id.mapped(
                    "product_capacity_ids"
                ).filtered(lambda l: l.product_id.id == cemetery_product.id)
                available_space += storage_cap.quantity
                occupied_space += sum(
                    stock_quant_obj.search([("location_id", "=", location.id)]).mapped(
                        "quantity"
                    )
                )
            cemetery.available_space = available_space - occupied_space
            cemetery.occupied_space = occupied_space

    @api.model_create_multi
    def create(self, vals_list):
        cemeteries = super().create(vals_list)
        StockLocation = self.env["stock.location"]
        CemeteryLocation = self.env["cemetery.location"]
        li = []
        for cemetery in cemeteries:
            locations = StockLocation.search(
                [("warehouse_id", "=", cemetery.warehouse_id.id)]
            )
            for location in locations:
                location.write({"is_cemetery_location": True})
                li.append(
                    {"cemetery_id": cemetery.id, "location_cemetery_id": location.id}
                )
        CemeteryLocation.create(li)
        return cemeteries

    @api.model
    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)
        if self._context.get("default_is_cemetery"):
            count = (
                self.env["cemetery"]
                .with_context(active_test=False)
                .search_count(
                    [
                        ("company_id", "=", self.env.company.id),
                        ("is_cemetery", "=", True),
                    ]
                )
            )
            defaults["name"] = (
                "%s - Cemetery # %s" % (self.env.company.name, count + 1)
                if count
                else self.env.company.name
            )
        return defaults
