# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class Cemetery(models.Model):
    _name = "cemetery"
    _description = "Cemetery"

    warehouse_id = fields.Many2one(
        "stock.warehouse", "Warehouse", required=True, ondelete="cascade", delegate=True
    )

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
