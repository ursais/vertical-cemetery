# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_cemetery_beneficiary = fields.Boolean("Cemetery Beneficiary?", default=False)
    cemetery_beneficiary_type = fields.Selection(
        selection=[
            ("deceased", "Deceased"),
            ("rights_holder", "Rightsholder")
        ],
        string="Beneficiary type",
    )

    is_cemetery_location = fields.Boolean("Cemetery Location?")
    beneficiary_id = fields.Many2one("cemetery.beneficiary", string="Beneficiary")
    cemetery_id = fields.Many2one("cemetery", string="Cemetery")

    @api.model
    def create(self, vals):
        cemetery_beneficiary = None

        # First, create the partner record
        partner = super().create(vals)

        # Check if the partner is marked as a cemetery beneficiary
        if vals.get('is_cemetery_beneficiary', True):
            # Prepare the beneficiary values
            beneficiary_type = vals.get('cemetery_beneficiary_type') or self.env.context.get('default_cemetery_beneficiary_type') or 'rights_holder'
            beneficiary_vals = {
                'name': vals.get('name', 'New Beneficiary'),
                'beneficiary_type': beneficiary_type,
                'partner_id': partner.id,  # Assign the correct partner_id
            }
            # Create the cemetery beneficiary
            cemetery_beneficiary = self.env['cemetery.beneficiary'].create(beneficiary_vals)

            # Set the beneficiary_id on the partner
            partner.beneficiary_id = cemetery_beneficiary.id

        return partner

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        domain = domain or []
        if self._context.get("is_cemetery_location"):
            domain += [("is_cemetery_location", "=", True)]
        if self._context.get("is_cemetery_partner"):
            domain += [("is_cemetery_beneficiary", "=", True)]
        res = super()._name_search(name, domain, operator, limit, order)
        return res

