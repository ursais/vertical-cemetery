# Copyright (C) 2025 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

def _activate_stock_settings(env):

    # Find res.config.settings
    stock_settings = env['res.config.settings'].sudo().search([], limit=1)

    # Activate the settings
    stock_settings.write({'group_stock_multi_locations': True})
    stock_settings.write({'group_stock_storage_categories': True})

    # Save your changes
    stock_settings.set_values()
