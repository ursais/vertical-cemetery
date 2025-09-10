# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from email.policy import default

from odoo import fields, models, api

class StockMove(models.Model):
    _inherit = "stock.move"

    cemetery_operation_line_id = fields.Many2one('cemetery.operation.line')
    is_cemetery = fields.Boolean()


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    cemetery_operation_line_id = fields.Many2one('cemetery.operation.line')
    is_cemetery = fields.Boolean(compute="_compute_is_cemetery", default=False, store=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if self._context.get("is_cemetery_move"):
            cemetery_product_ids = (
                self.env.company.cemetery_product_template.product_variant_ids.ids
            )
            domain += [("product_id", "in", cemetery_product_ids)]
        return super()._search(domain, offset, limit, order, access_rights_uid)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if self.product_id.is_cemetery_beneficiary:
            self.is_cemetery = True
        return res

    @api.depends("product_id")
    def _compute_is_cemetery(self):
        for record in self:
            if record.product_id.is_cemetery_beneficiary:
                record.is_cemetery = True
