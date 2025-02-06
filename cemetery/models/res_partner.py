# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class Partners(models.Model):
    _inherit = "res.partner"

    is_cemetery_beneficiary = fields.Boolean("Cemetery Beneficiary?")
    cemetery_beneficiary_type = fields.Selection(
        selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")],
        string="Beneficiary type",
    )
    is_cemetery_location = fields.Boolean("Cemetery Location?")
    beneficiary_id = fields.Many2one("cemetery.beneficiary", string="Beneficiary")
    cemetery_id = fields.Many2one("cemetery", string="Cemetery")

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        domain = domain or []
        if self._context.get("is_cemetery_location"):
            domain += [("is_cemetery_location", "=", True)]
        if self._context.get("is_cemetery_partner"):
            domain += [("is_cemetery_beneficiary", "=", True)]
        return self._search(domain, limit=limit, order=order)
