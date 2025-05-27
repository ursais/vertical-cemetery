# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models, fields
from odoo.exceptions import UserError


class CemeteryConvert(models.TransientModel):
    _name = "cemetery.convert"
    _description = "Convert contacts and addresses into cemetery records"

    cemetery_type = fields.Selection(
        selection=[
            ("cemetery", "Cemetery"),
            ("concession", "Concession"),
            ("columbarium", "Columbarium"),
            ("common_ground", "Common Ground"),
            ("ossuary", "Ossuary"),
            ("deceased", "Deceased"),
            ("rights_holder", "Rights Holder"),
        ],
        string="Cemetery type",
    )
    cemetery_id = fields.Many2one("cemetery")
    cemetery_location_id = fields.Many2one(
        "cemetery.location", string="Current Location"
    )
    is_reserve_location = fields.Boolean()

    def action_create_cemetery_warehouse(self, partner):
        CemeteryWarehouse = self.env["cemetery"].with_context(active_test=False)
        CemeteryWarehouse.create(
            {"name": partner.name, "code": partner.name, "is_cemetery": True,}
        )

    def action_create_cemetery_location(self, partner, parent, reserve_location):
        CemeteryLocation = self.env["cemetery.location"].with_context(active_test=False)
        existing_location = CemeteryLocation.search([("partner_id", "=", partner.id)])
        location_id = self.env["stock.location"].search(
            [
                ("warehouse_id", "=", self.cemetery_id.warehouse_id.id),
                ("usage", "=", "internal"),
            ],
            limit=1,
        )
        cemetery_location = self.env["cemetery.location"].search(
            [("location_cemetery_id", "=", location_id.id)]
        )
        if existing_location:
            raise UserError(_("This Cemetery Location already exists."))
        location = CemeteryLocation.create(
            {
                "name": partner.name,
                "partner_id": partner.id,
                "is_cemetery_location": True,
                "cemetery_id": self.cemetery_id.id,
                "location_id": cemetery_location.id,
                "parent_id": parent.id,
                "is_reserve_location": reserve_location,
            }
        )
        partner.write({"is_cemetery_location": True})
        location.location_cemetery_id.write(
            {
                "cemetery_location_type": self.cemetery_type,
                "warehouse_id": self.cemetery_id.warehouse_id.id,
                "location_id": location_id.id,
            }
        )

    def action_create_cemetery_beneficiary(self, partner):
        CemeteryBeneficiary = self.env["cemetery.beneficiary"].with_context(
            active_test=False, with_partner_id=partner.id
        )
        location_id = self.env["stock.location"].search(
            [
                ("warehouse_id", "=", self.cemetery_id.warehouse_id.id),
                ("usage", "=", "internal"),
            ],
            limit=1,
        )
        cemetery_location = self.env["cemetery.location"].search(
            [("location_cemetery_id", "=", location_id.id)]
        )
        partner.write(
            {
                "is_cemetery_beneficiary": True,
                "cemetery_beneficiary_type": self.cemetery_type,
                "cemetery_id": self.cemetery_id.id,
            }
        )
        CemeteryBeneficiary.create(
            {
                "name": partner.name,
                "partner_id": partner.id,
                "serial_number": partner.id,
                "beneficiary_type": self.cemetery_type,
                "cemetery_location_id": self.cemetery_location_id.id,
            }
        )

    def action_convert(self):
        partners = self.env["res.partner"].browse(self._context.get("active_ids", []))
        for partner in partners:
            if self.cemetery_type == "cemetery":
                self.action_create_cemetery_warehouse(partner)
            elif self.cemetery_type in [
                "concession",
                "columbarium",
                "common_ground",
                "ossuary",
            ]:
                self.action_create_cemetery_location(partner, self.cemetery_location_id, self.is_reserve_location)
            elif self.cemetery_type in ["deceased", "rights_holder"]:
                self.action_create_cemetery_beneficiary(partner)
