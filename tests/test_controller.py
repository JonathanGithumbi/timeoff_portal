import unittest
from odoo.tests import TransactionCase


class TestMyController(TransactionCase):
    def setUp(self):
        super(TestMyController, self).setUp()

        # Create a test user and employee
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testpass',
        })
        self.test_employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': self.test_user.id,
        })

        # Create some leave records for the test employee
        self.env['hr.leave'].create([{
            'employee_id': self.test_employee.id,
            'state': 'confirm',
        } for _ in range(5)])

    def test_prepare_home_portal_values(self):
        # Log in as the test user
        self.env = self.env(user=self.test_user)

        # Call the method to be tested
        values = self.env['my_module.my_controller']._prepare_home_portal_values(counters)

        # Check that the leave count is correct
        self.assertEqual(values['leave_count'], 5)


if __name__ == '__main__':
    unittest.main()
