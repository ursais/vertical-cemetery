# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    is_cemetery = fields.Boolean("Cemetery?", compute="_compute_is_cemetery", default=False, store=True)

    @api.depends("product_id")
    def _compute_is_cemetery(self):
        for record in self:
            if record.product_id.is_cemetery_beneficiary:
                record.is_cemetery = True
