# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_cemetery_beneficiary = fields.Boolean("Cemetery Beneficiary?")

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        domain = domain or []
        if self._context.get("is_cemetery_beneficiary"):
            domain += [("is_cemetery_beneficiary", "=", True)]
        return self._search(domain, limit=limit, order=order)
