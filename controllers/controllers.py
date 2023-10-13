import odoo.exceptions
from odoo.addons.portal.controllers.portal import CustomerPortal,pager
from odoo.http import request
from odoo import http
from datetime import datetime,time
import psycopg2
from datetime import datetime, timedelta
import pytz


class leavePortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        #Get the currently logged in employee
        #Fetch all leave records belonging to that employee from the hr.leave model, which have the status 'approve' and 'confirm'
        #Count the resulting records

        User = request.env['res.users']
        employee_id = User.browse(request.uid).employee_id
        if employee_id:
            leave_count = request.env['hr.leave'].search_count([
                ('employee_id', '=', employee_id.id),

            ])

        values['leave_count'] = leave_count

        #Time off module disappears when the leave count is 0. return 1  so that its visiblle whether or not there are leaves
        if leave_count != 0:
            return values
        else:
            values['leave_count'] = 'None'
            return values

    @http.route([ '/my/leaves'],type='http',website=True)
    def Leaves(self,sortby="date_from",**kw):

        # Sorting Feature
        sorted_list = {
            'date_from': {'label': 'Start Date', 'order': 'date_from desc'},
            'date_to': {'label': 'End Date', 'order': 'date_to'},
            'holiday_status_id': {'label': 'Leave Type', 'order': 'holiday_status_id'},
            'state': {'label': 'Status', 'order': 'state'}
        }
        default_order_by = sorted_list[sortby]['order']

        current_user = http.request.env.user
        leaves = http.request.env['hr.leave'].search([('user_id', '=', current_user.id)],order=default_order_by)

        #Leave allocations
        #Get allocation instance
        hr_leave_allocation = request.env['hr.leave.allocation']
        # Fetch leave allocations for the currently logged-in user
        leave_allocations = hr_leave_allocation.search([('employee_id.user_id', '=', current_user.id)])

        return request.render('timeoff_portal.leaves_list_view',{
            'leaves':leaves,
            'allocations':leave_allocations,
            'page_name':'leaves_list_view',
            'sortby':sortby,
            'searchbar_sortings':sorted_list
        })

    def calculate_date_from(self,employee, date_string):
        # Get the timezone of the employee
        employee_tz = pytz.timezone(employee.tz)

        # Convert the date string to a datetime object
        date = datetime.strptime(date_string, '%Y-%m-%d')

        # Localize the date to the employee's timezone
        local_date = employee_tz.localize(date)

        # Define the start time as 8:00 in the employee's timezone
        start_time = local_date.replace(hour=8, minute=0, second=0, microsecond=0)

        # Convert the timezone-aware datetime to a naive datetime in UTC
        start_time = start_time.astimezone(pytz.UTC).replace(tzinfo=None)

        return start_time

    def calculate_date_to(self,employee, date_string):
        # Get the timezone of the employee
        employee_tz = pytz.timezone(employee.tz)

        # Convert the date string to a datetime object
        date = datetime.strptime(date_string, '%Y-%m-%d')

        # Localize the date to the employee's timezone
        local_date = employee_tz.localize(date)

        # Define the start time as 8:00 in the employee's timezone
        start_time = local_date.replace(hour=17, minute=0, second=0, microsecond=0)

        # Convert the timezone-aware datetime to a naive datetime in UTC
        start_time = start_time.astimezone(pytz.UTC).replace(tzinfo=None)

        return start_time


    @http.route('/new/leave-request', methods=['POST','GET'],type='http', auth='user',website=True)
    def NewLeaveRequest(self, **kw):

        # Get the current user
        current_user = http.request.env.user

        # Search for the employee record that matches the current user
        employee = request.env['hr.employee'].search([('user_id', '=', current_user.id)], limit=1)

        leave_types = request.env['hr.leave.type'].sudo().search([('active', '=', True)])

        leave_types_with_balance = leave_types.filtered(
            lambda lt: lt.remaining_leaves > 0)

        vals = {'leave_types':leave_types_with_balance,'page_name':'new_leave_request'}


        if request.httprequest.method == 'POST':
            error_list = []
            if not kw.get('description'):
                error_list.append('Please add a note/description to send along with the request')
            if not kw.get('from_date'):
                error_list.append('Please add a date for the commencement of the leave')
            if not kw.get('to_date'):
                error_list.append('Please add a date for the end of the leave')
            if not kw.get('time_off_type'):
                error_list.append('Please select a time off type from the menu')
            if not kw.get('time_off_type').isdigit():
                error_list.append('Invalid Leave Type')
            # if not self.validate_dates(kw.get('from_date'),kw.get('to_date')):
            #     error_list.append('The "To date" cannot come before "From date".Please verify the ordering of your dates.')
            if not error_list:
                try:
                    request.env['hr.leave'].create({
                        'employee_id': request.env['hr.employee'].search([('user_id', '=', request.env.uid)],
                                                                         limit=1).id, 'name': kw.get('description'),
                        'request_date_from': kw.get('from_date'),
                        'request_date_to':kw.get('to_date'),
                        'date_from':self.calculate_date_from(employee,kw.get('from_date')),
                        'date_to':self.calculate_date_to(employee,kw.get('to_date')),
                        'holiday_status_id': int(kw.get('time_off_type')),
                        'holiday_type': kw.get('holiday_type')
                    })
                except odoo.exceptions.ValidationError as e:#Catch Leave date overlap issue
                    request.env.cr.rollback()#rollback uncommited database transacttions
                    error_list.append(e.__str__())#
                    vals['error_list'] = error_list
                    return request.render('timeoff_portal.leaves_form_view', vals)
                except psycopg2.errors.CheckViolation as e:
                    request.env.cr.rollback()  # rollback uncommited database transacttions
                    error_list.append("Date Error. 'To date' cannot come before 'From Date'")  #
                    vals['error_list'] = error_list
                    return request.render('timeoff_portal.leaves_form_view', vals)
                else:
                    success = "Leave Request Submitted Successfully"
                    vals['success_msg'] = success
            else:
                vals['error_list'] = error_list

        return request.render('timeoff_portal.leaves_form_view',vals)

    @http.route(['/my/record/delete/<model("hr.leave"):rec>'], type='http', auth="user", website=True)
    def DeleteLeaveRequest(self,rec):
        vals = {}
        try:
            rec.unlink()
        except Exception as e:
            error_msg = str(e)
            vals['error_msg'] = error_msg
        else:
            success_msg = "Successfully revoked leave request."
            vals['success_msg'] = success_msg
        return request.redirect('/my/leaves')

