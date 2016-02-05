# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
import calendar
from itertools import islice

total_principal = float(4900000)
interest = float(12.4)
interest_rate = float(interest / 100)
monthly_interest = float(interest_rate / 12)

# срок кредита
years = 20
months = years * 12
start_date = datetime.date(2012, 4, 18)

monthly_payment = round(float(total_principal * (monthly_interest / (1 - (1 + monthly_interest) ** (- months)))), 2)
print(monthly_payment)

class Payment(object):
    def __init__(self, date, interest_payment, principal_payment, current_principal):
        self.date = date
        self.interest_payment = interest_payment
        self.principal_payment = principal_payment
        self.current_principal = current_principal
    
    def __str__(self):
        return '%s - %.2f - %.2f - %.2f' % (str(self.date), self.interest_payment, self.principal_payment, self.current_principal)

# how much days in the year
def days_in_year(year):
    return 366 if calendar.isleap(year) else 365

# generating regular payments
current_principal = total_principal
payments = {}
for m in range(1, months + 1):
    pay_date = start_date + relativedelta(months=m)
    
    # первый месяц в году, т.е. январь
    # в этом случае надо немного по-другому считать
    if pay_date.month == 1:
        prev_pay_date = payments[m - 1].date
        december31 = datetime.date(prev_pay_date.year, 12, 31)
        
        days1 = december31 - prev_pay_date
        days1 = days1.days
        p1 = days1 / days_in_year(prev_pay_date.year)
        
        days2 = pay_date - december31
        days2 = days2.days
        p2 = days2 / days_in_year(pay_date.year)
                
        interest_payment = round(float( current_principal * interest_rate * (p1 + p2) ), 2)
    else:
        if m == 1: # first payment
            d = pay_date - start_date
            days = d.days
        else:
            d = pay_date - payments[m - 1].date
            days = d.days
        
        interest_payment = round(float(current_principal * interest_rate * days) / float(days_in_year(pay_date.year)), 2)
        
        if m == 240:
            monthly_payment = current_principal + interest_payment
    
    principal_payment = round(float(monthly_payment - interest_payment), 2)
     
    current_principal -= principal_payment
    
    payments[m] = Payment(pay_date, interest_payment, principal_payment, current_principal)

#for k, v in islice(payments.items(), 88):
for k, v in payments.items():
    print(str(v))