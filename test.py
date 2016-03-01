import unittest
import datetime
import mortgage
from decimal import Decimal
import csv
from collections import defaultdict

class Test_test1(unittest.TestCase):

    def find_payments(self, payments, date):
        return payments.get(date, None)

    def compare_with_etalon(self, etalon_csv, payments):
        with open(etalon_csv, encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader, None)  # skip the header
            pays = []
            for row in reader:
                date = datetime.datetime.strptime(row[0], '%d.%m.%Y').date()
                row = [Decimal(item.replace(" ", "").replace(',', '.')) for item in row[1:]]
                if len(pays) == 0:
                    pays = self.find_payments(payments, date)
                    self.assertNotEqual(pays, list(), "Payment for '%s' date not found" % (date,))

                pay = pays.pop(0)
                self.assertEqual(pay.payment, row[0], 'date: %s' % date)
                self.assertEqual(pay.principal_payment, row[2], 'date: %s' % date)
                self.assertEqual(pay.interest_payment, row[3], 'date: %s' % date)
                self.assertEqual(pay.current_principal, row[4], 'date: %s' % date)

    def test_loan_1(self):

        m = mortgage.Mortgage(12.4, 12*20, datetime.date(2012, 4, 18))
        self.compare_with_etalon('test_data/loan1.csv', m.calc(4900000).payments)

    def test_loan_2(self):

        m = mortgage.Mortgage(12.4, 12*20, datetime.date(2012, 4, 18))
        lst = defaultdict(list)
        mortgage.add_non_reg_payment(lst, 18, 2016, 1, 15, 800000)
        self.compare_with_etalon('test_data/loan2.csv', m.calc(4900000, lst).payments)

    def test_loan_3(self):
        
        m = mortgage.Mortgage(12.4, 12*20, datetime.date(2012, 4, 18))

        lst = defaultdict(list)
        mortgage.add_non_reg_payment(lst, 18, 2016, 1, 15, 800000)
        mortgage.add_non_reg_payment(lst, 18, 2016, 2, 18, 10000)
        self.compare_with_etalon('test_data/loan3.csv', m.calc(4900000, lst).payments)

if __name__ == '__main__':
    unittest.main()