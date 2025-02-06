# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockWarehous(models.Model):
    _inherit = "stock.warehouse"

    is_cemetery = fields.Boolean("Cemetery?")
