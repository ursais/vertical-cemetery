# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if self._context.get("is_cemetery_move"):
            cemetery_product_ids = (
                self.env.company.cemetery_product_template.product_variant_ids.ids
            )
            domain += [("product_id", "in", cemetery_product_ids)]
        return super()._search(domain, offset, limit, order, access_rights_uid)
