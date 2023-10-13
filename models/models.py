from odoo import models,api

class TimeOffPortal(models.Model):
    _inherit = 'hr.leave'

    @api.model_create_multi
    def create(self, vals_list):
        return super(TimeOffPortal, self).create(vals_list)