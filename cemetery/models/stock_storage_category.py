# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockStorageCategory(models.Model):
    _inherit = "stock.storage.category"

    is_cemetery = fields.Boolean("Cemetery?")
