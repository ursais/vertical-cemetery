from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    cemetery_product_template = fields.Many2one(
        "product.template", string="Configure Cemetery Product"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cemetery_product_template = fields.Many2one(
        "product.template",
        string="Configure Cemetery Product",
        related="company_id.cemetery_product_template",
        readonly=False,
    )
