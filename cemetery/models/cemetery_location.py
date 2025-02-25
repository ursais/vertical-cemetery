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
    beneficiary_ids = fields.One2many("cemetery.beneficiary", "cemetery_location_id", readonly=True)

    @api.depends("cemetery_id")
    def _compute_display_name(self):
        for location in self:
            location.display_name = str(location.cemetery_id.code) + "/" + str(location.name)
