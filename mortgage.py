# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
import calendar
from itertools import islice
import math

total_principal = float(4900000)
interest = float(12.4)
interest_rate = float(interest / 100)
monthly_interest = float(interest_rate / 12)

# срок кредита
years = 20
total_months = years * 12
start_date = datetime.date(2012, 4, 18)

def calc_monthly_payment(principal, monthly_interest, months):
    return round(float(principal * (monthly_interest / (1 - (1 + monthly_interest) ** (- months)))), 2)

# how much days in the year
def days_in_year(year):
    return 366 if calendar.isleap(year) else 365
   
class Payment(object):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal):
        self.date = date
        self.payment = payment
        self.interest_payment = interest_payment
        self.principal_payment = principal_payment
        self.current_principal = current_principal
    
    def __str__(self):
        return '%s - %.2f - %.2f - %.2f - %.2f' % (str(self.date), self.payment, self.interest_payment, self.principal_payment, self.current_principal)

class RegularPayment(Payment):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal):
        return super().__init__(date, payment, interest_payment, principal_payment, current_principal)

class NonRegularPayment(Payment):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal, payment_in_regular_date):
        super().__init__(date, payment, interest_payment, principal_payment, current_principal)
        self.payment_in_regular_date = payment_in_regular_date
        self.paid = False

planned_non_regular_payments = [
    NonRegularPayment(datetime.date(2016, 1, 15), round(float(800000.), 2), 0, 0, 0, False),
]

def find_reqular_payment(start, end):
    lst = []
    for i, p in enumerate(planned_non_regular_payments):
        if start <= p.date <= end and not p.paid:
            lst.append(p)
    return lst

def calc_interest_payment(pay_date, prev_pay_date, principal, interest_rate):
    # первый месяц в году, т.е. январь
    # в этом случае надо немного по-другому считать
    if pay_date.month == 1:
        december31 = datetime.date(prev_pay_date.year, 12, 31)
        
        days1 = december31 - prev_pay_date
        days1 = days1.days
        p1 = days1 / days_in_year(prev_pay_date.year)
        interest_payment1 = round(float( principal * interest_rate * p1), 2)
        
        days2 = pay_date - december31
        days2 = days2.days
        p2 = days2 / days_in_year(pay_date.year)        
        interest_payment2 = round(float( principal * interest_rate * p2 ), 2)
        
        interest_payment = interest_payment1 + interest_payment2
    else:    
        d = pay_date - prev_pay_date
        days = d.days
        
        interest_payment = round(float(principal * interest_rate * days) / float(days_in_year(pay_date.year)), 2)
        
    return interest_payment

def diff_dates(dt1, dt2):
    diff = relativedelta(dt1, dt2)
    return diff.years * 12 + diff.months

# generating payments
first_monthly_payment = monthly_payment = calc_monthly_payment(total_principal, monthly_interest, total_months)
print(monthly_payment)

current_principal = total_principal
payments = []

class Period(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.payments = []
        self.principal_paid = False

    def add_payment(self, payment):
        self.payments.append(payment)

periods = []
cur_period = start_date
mode1 = True # если True, каждый месяц добавляем в досрочку разницу между текущим ежемесячным платежём и первоначальным
for m in range(1, total_months + 1):
    end_period = start_date + relativedelta(months=m)
    period = Period(cur_period, end_period)

    non_reg_payments = find_reqular_payment(cur_period, end_period)
    for non_reg_pay in non_reg_payments:
        if non_reg_pay and not non_reg_pay.payment_in_regular_date:
            # считаем набежавшие проценты от последнего платежа до даты досрочки
            p1 = calc_interest_payment(non_reg_pay.date, cur_period, current_principal, interest_rate)
            p1 = round(p1, 2)

            if non_reg_pay.payment < p1:
                pass # не хватает для выплаты процентов
            else:
                # обновим остаток долга с учётом процентов
                current_principal -= non_reg_pay.payment - p1
                current_principal = round(current_principal, 2)

                # обновим инфу о платеже и добавим её в список платежей
                non_reg_pay.interest_payment = p1
                non_reg_pay.current_principal = current_principal
                non_reg_pay.principal_payment = round(non_reg_pay.payment, 2) - p1

                # в этом периоде больше за основной долг не платим
                period.principal_paid = True if not non_reg_pay.payment_in_regular_date else False
                period.add_payment(non_reg_pay)

                if current_principal > 0:
                    # так как долг поменялся, пересчитаем аннуитентный платёж
                    left_months = total_months - m # сколько месяцев осталось платить
                    monthly_payment = calc_monthly_payment(current_principal, monthly_interest, left_months)

                    if mode1:
                        # вот эту разницу будем добавлять в досрочку в дату очередного регулярного платежа
                        v = round(first_monthly_payment - monthly_payment, 2)
                        if v < 10000:
                            v = 10000
                        else:
                            v = math.ceil(v / 1000) * 1000

                        if v > current_principal: # осталось заплатить меньше, чем получившаяся разница
                            interest_payment = round(calc_interest_payment(end_period + relativedelta(months=1), cur_period + relativedelta(months=1), current_principal, interest_rate), 2)
                            principal_payment = round(float(monthly_payment - interest_payment), 2)
                            v = current_principal - principal_payment
                            planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))
                        else:
                            planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))

                non_reg_pay.paid = True
                cur_period = non_reg_pay.date
    
    # регулярный платёж

    interest_payment = round(calc_interest_payment(end_period, cur_period, current_principal, interest_rate), 2)

    if m == total_months and monthly_payment > current_principal: # last payment
        principal_payment = current_principal
        monthly_payment = interest_payment + principal_payment
    elif not period.principal_paid:
        principal_payment = round(float(monthly_payment - interest_payment), 2)
    else:
        principal_payment = 0

    current_principal -= principal_payment
    current_principal = round(current_principal, 2)

    period.add_payment(Payment(end_period, interest_payment + principal_payment, interest_payment, principal_payment, current_principal))
    period.principal_paid = True

    has_non_reg_pay = False
    for non_reg_pay in non_reg_payments:
        if non_reg_pay and non_reg_pay.payment_in_regular_date:
            current_principal -= non_reg_pay.payment
            current_principal = round(current_principal, 2)

            non_reg_pay.current_principal = current_principal
            non_reg_pay.principal_payment = non_reg_pay.payment
            non_reg_pay.paid = True
            period.add_payment(non_reg_pay)
            has_non_reg_pay = True

    if has_non_reg_pay and current_principal > 0:
        # так как долг поменялся, пересчитаем аннуитентный платёж
        left_months = total_months - m # сколько месяцев осталось платить
        monthly_payment = calc_monthly_payment(current_principal, monthly_interest, left_months)

        if mode1:
            # вот эту разницу будем добавлять в досрочку в дату очередного регулярного платежа
            v = round(first_monthly_payment - monthly_payment, 2)
            v = math.ceil(v / 1000) * 1000 # округлим до тысячи в большую сторону
            if v > current_principal: # осталось заплатить меньше, чем получившаяся разница
                # скорректируем платёж
                interest_payment = round(calc_interest_payment(end_period + relativedelta(months=1), cur_period + relativedelta(months=1), current_principal, interest_rate), 2)
                principal_payment = round(float(monthly_payment - interest_payment), 2)
                v = current_principal - principal_payment
                planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))
            else:
                planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))

    periods.append(period)
    if current_principal == 0:
        break

    cur_period = end_period

for p in periods:
    for pay in p.payments:
        print(str(pay))