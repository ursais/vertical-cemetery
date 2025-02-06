# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockWarehous(models.Model):
    _inherit = "stock.location"

    cemetery_location_type = fields.Selection(
        selection=[
            ("concession", "Concession"),
            ("columbarium", "Columbarium"),
            ("ossuary", "Ossuary"),
            ("common_ground", "Common ground"),
        ],
        string="Cemetery location type",
    )
    is_cemetery_location = fields.Boolean("Cemetery Location?")
