import unittest
import datetime
import mortgage
from money import Money
import csv

class Test_test1(unittest.TestCase):

    def find_payment(self, periods, date):
        for p in periods:
            for pay in p.payments:
                if pay.date == date:
                    return pay
        return None

    def compare_with_etalon(self, etalon_csv, periods):
        with open(etalon_csv, encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader, None)  # skip the header
            for row in reader:
                date = datetime.datetime.strptime(row[0], '%d.%m.%Y').date()
                row = [Money(item.replace(" ", "").replace(',', '.'), 'RUB') for item in row[1:]]
                pay = self.find_payment(periods, date)
                self.assertIsNotNone(pay, "Payment for '%s' date not found" % (date,))

                self.assertEqual(pay.payment, row[0], 'date: %s' % date)
                self.assertEqual(pay.principal_payment, row[2], 'date: %s' % date)
                self.assertEqual(pay.interest_payment, row[3], 'date: %s' % date)
                self.assertEqual(pay.current_principal, row[4], 'date: %s' % date)

    def test_loan_1(self):

        m = mortgage.Mortgage(4900000, 12.4, 12*20, datetime.date(2012, 4, 18), [], False)
        self.compare_with_etalon('test_data/loan1.csv', m.calc())

    def test_loan_2(self):

        m = mortgage.Mortgage(4900000, 12.4, 12*20, datetime.date(2012, 4, 18),
                              [
                                  mortgage.make_non_reg_payment(2016, 1, 15, 800000)
                              ],
                              False
        )

        self.compare_with_etalon('test_data/loan2.csv', m.calc())

if __name__ == '__main__':
    unittest.main()
