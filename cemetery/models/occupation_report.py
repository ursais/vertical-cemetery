from odoo import tools
from odoo import api, fields, models


class StockReport(models.Model):
    _name = "occupation.report"
    _description = "Occupation Report"
    _rec_name = "id"
    _auto = False

    id = fields.Integer("", readonly=True)
    cemetery_location_id = fields.Many2one(
        "cemetery.location", string="Cemetery Location"
    )
    location_id = fields.Many2one("stock.location", string="Location")
    warehouse_id = fields.Many2one("stock.warehouse")
    partner_id = fields.Many2one("res.partner")
    available_space = fields.Integer()
    occupied_space = fields.Integer()
    serial_id = fields.Many2one("stock.lot")
    cemetery_beneficiary_type = fields.Selection(
        selection=[("deceased", "Deceased"), ("rights_holder", "Rightsholder")],
        string="Beneficiary type",
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Define the SELECT part
        select_clause = """
            DISTINCT
            l.id AS id,
            l.id AS location_id,
            w.id AS warehouse_id,
            p.id AS partner_id,
            sl.id AS serial_id,
            cw.beneficiary_type AS cemetery_beneficiary_type,
            sq.quantity AS occupied_space,
            sscc.quantity - sq.quantity AS remaining_quantity
        """

        # Define the FROM part
        from_clause = """
            stock_location AS l
            JOIN stock_warehouse AS w ON l.warehouse_id = w.id
            JOIN cemetery_location AS cl ON l.id = cl.location_cemetery_id
            JOIN cemetery_beneficiary AS cw ON cw.cemetery_location_id = cl.id
            JOIN res_partner AS p ON p.id = cw.partner_id
            JOIN stock_lot AS sl ON sl.id = cw.serial_id
            JOIN stock_quant AS sq ON sq.location_id = l.id
            JOIN stock_storage_category_capacity AS sscc ON sscc.storage_category_id = l.storage_category_id
        """

        # Define the GROUP BY part
        group_by_clause = "l.id, l.name, w.name, p.name, sl.name, cw.beneficiary_type, sq.quantity, sscc.quantity"

        # Create or replace the view
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
                                SELECT
                                    %s
                                FROM
                                    %s
                                WHERE
                                    l.is_cemetery_location = 't'
                                    AND w.is_cemetery = 't'
                                GROUP BY
                                    %s
                )"""
            % (self._table, select_clause, from_clause, group_by_clause)
        )
