# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
import calendar
from itertools import islice
import math
from decimal import Decimal
from money import Money

# how much days in the year
def days_in_year(year):
    return 366 if calendar.isleap(year) else 365

def diff_dates(dt1, dt2):
    diff = relativedelta(dt1, dt2)
    return diff.years * 12 + diff.months   

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

class Period(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.payments = []
        self.principal_paid = False

    def add_payment(self, payment):
        self.payments.append(payment)

class Mortgage(object):
    def __init__(self, principal, interest, months, start_date, non_reg_payments, mode):
        self.total_principal = Money(principal, 'RUB')
        self.interest = interest
        self.interest_rate = Decimal(interest / 100)
        self.monthly_interest = Decimal(self.interest_rate / 12)
        self.mode1 = mode # если True, каждый месяц добавляем в досрочку разницу между текущим ежемесячным платежём и первоначальным

        # срок кредита
        self.total_months = months
        self.start_date = start_date

        self.planned_non_regular_payments = non_reg_payments

    def calc_monthly_payment(self, principal, months):
        return Money(round(principal.amount * (self.monthly_interest / (1 - (1 + self.monthly_interest) ** (- months))), 2), 'RUB')

    def find_reqular_payment(self, start, end):
        lst = []
        for i, p in enumerate(self.planned_non_regular_payments):
            if start <= p.date <= end and not p.paid:
                lst.append(p)
        return lst

    def calc_interest_payment(self, pay_date, prev_pay_date, principal):
        # первый месяц в году, т.е. январь
        # в этом случае надо немного по-другому считать
        if pay_date.month == 1:
            december31 = datetime.date(prev_pay_date.year, 12, 31)
        
            days1 = december31 - prev_pay_date
            days1 = days1.days
            p1 = Decimal(days1 / days_in_year(prev_pay_date.year))
            interest_payment1 = Money(round(principal.amount * self.interest_rate * p1, 2), 'RUB')
        
            days2 = pay_date - december31
            days2 = days2.days
            p2 = Decimal(days2 / days_in_year(pay_date.year))
            interest_payment2 = Money(round(principal.amount * self.interest_rate * p2, 2), 'RUB')
        
            interest_payment = interest_payment1 + interest_payment2
        else:    
            d = pay_date - prev_pay_date
            days = d.days
        
            interest_payment = Money(round(principal.amount * self.interest_rate * days / days_in_year(pay_date.year), 2), 'RUB')
        
        return interest_payment

    def calc(self):
        # generating payments

        current_principal = self.total_principal
        first_monthly_payment = monthly_payment = self.calc_monthly_payment(current_principal, self.total_months)

        payments = []
        periods = []
        cur_period = self.start_date

        for m in range(1, self.total_months + 1):
            end_period = self.start_date + relativedelta(months=m)
            period = Period(cur_period, end_period)

            non_reg_payments = self.find_reqular_payment(cur_period, end_period)
            for non_reg_pay in non_reg_payments:
                if non_reg_pay and not non_reg_pay.payment_in_regular_date:
                    # считаем набежавшие проценты от последнего платежа до даты досрочки
                    p1 = self.calc_interest_payment(non_reg_pay.date, cur_period, current_principal)

                    if non_reg_pay.payment < p1:
                        pass # не хватает для выплаты процентов
                    else:
                        # обновим остаток долга с учётом процентов
                        current_principal -= non_reg_pay.payment - p1

                        # обновим инфу о платеже и добавим её в список платежей
                        non_reg_pay.interest_payment = p1
                        non_reg_pay.current_principal = current_principal
                        non_reg_pay.principal_payment = non_reg_pay.payment - p1

                        period.principal_paid = True # в этом периоде больше за основной долг не платим
                        period.add_payment(non_reg_pay)

                        if current_principal > 0:
                            # так как долг поменялся, пересчитаем аннуитентный платёж
                            left_months = self.total_months - m # сколько месяцев осталось платить
                            monthly_payment = self.calc_monthly_payment(current_principal, left_months)

                            if self.mode1:
                                # вот эту разницу будем добавлять в досрочку в дату очередного регулярного платежа
                                v = first_monthly_payment - monthly_payment
                                if v < 10000:
                                    v = 10000
                                else:
                                    v = math.ceil(v / 1000) * 1000 # округлим до тысячи в большую сторону

                                if v > current_principal: # осталось заплатить меньше, чем получившаяся разница
                                    interest_payment = self.calc_interest_payment(end_period + relativedelta(months=1), cur_period + relativedelta(months=1), current_principal)
                                    principal_payment = monthly_payment - interest_payment
                                    v = current_principal - principal_payment
                                    self.planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))
                                else:
                                    self.planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))

                        non_reg_pay.paid = True
                        cur_period = non_reg_pay.date
    
            # регулярный платёж

            interest_payment = self.calc_interest_payment(end_period, cur_period, current_principal)

            if m == self.total_months and monthly_payment > current_principal: # last payment
                principal_payment = current_principal
                monthly_payment = interest_payment + principal_payment
            elif not period.principal_paid:
                principal_payment = monthly_payment - interest_payment
            else:
                principal_payment = 0

            current_principal -= principal_payment

            period.add_payment(Payment(end_period, interest_payment + principal_payment, interest_payment, principal_payment, current_principal))
            period.principal_paid = True

            has_non_reg_pay = False
            for non_reg_pay in non_reg_payments:
                if non_reg_pay and non_reg_pay.payment_in_regular_date:
                    current_principal -= non_reg_pay.payment

                    non_reg_pay.current_principal = current_principal
                    non_reg_pay.principal_payment = non_reg_pay.payment
                    non_reg_pay.paid = True
                    period.add_payment(non_reg_pay)
                    has_non_reg_pay = True

            if has_non_reg_pay and current_principal > 0:
                # так как долг поменялся, пересчитаем аннуитентный платёж
                left_months = self.total_months - m # сколько месяцев осталось платить
                monthly_payment = self.calc_monthly_payment(current_principal, left_months)

                if self.mode1:
                    # вот эту разницу будем добавлять в досрочку в дату очередного регулярного платежа
                    v = first_monthly_payment - monthly_payment
                    v = math.ceil(v / 1000) * 1000 # округлим до тысячи в большую сторону
                    v += 1000

                    if v > current_principal: # осталось заплатить меньше, чем получившаяся разница
                        # скорректируем платёж
                        interest_payment = self.calc_interest_payment(end_period + relativedelta(months=1), cur_period + relativedelta(months=1), current_principal)
                        principal_payment = monthly_payment - interest_payment
                        v = current_principal - principal_payment
                        self.planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))
                    else:
                        self.planned_non_regular_payments.append(NonRegularPayment(end_period + relativedelta(months=1), v, 0, v, 0, True))

            periods.append(period)
            if current_principal == Money(0, 'RUB'):
                break

            cur_period = end_period

        return periods


def make_non_reg_payment(year, month, day, sum):
    return NonRegularPayment(datetime.date(year, month, day), round(sum, 2), 0, 0, 0, True if day == 18 else False)

m1 = Mortgage(
    float(4900000.), float(12.4), 12*20, datetime.date(2012, 4, 18),
    [
        make_non_reg_payment(2016, 1, 15, 800000),
        #make_non_reg_payment(2016, 5, 18, 75000),
        #make_non_reg_payment(2017, 1, 18, 77000),
        #make_non_reg_payment(2017, 5, 18, 61500),
        #make_non_reg_payment(2018, 5, 18, 54500),
        #make_non_reg_payment(2019, 5, 18, 49000),
        #make_non_reg_payment(2020, 5, 18, 43000),
        #make_non_reg_payment(2021, 5, 18, 36000),
        #make_non_reg_payment(2022, 5, 18, 28500),
        #make_non_reg_payment(2023, 5, 18, 20000),
        #make_non_reg_payment(2024, 5, 18, 10000),
        #make_non_reg_payment(2017, 1, 18, 911905),
    ],
    True
)

m2 = Mortgage(
    float(4900000.), float(12.4), 12*20, datetime.date(2012, 4, 18),
    [
        #NonRegularPayment(datetime.date(2016, 1, 15), round(float(800000.), 2), 0, 0, 0, False),
    ],
    False
)

def calc_interest_payments(year, periods):
    s = 0
    for p in periods:
        if p.end.year == year:
            for pay in p.payments:
                s += pay.interest_payment

    return s
periods1 = m1.calc()
#periods2 = m2.calc()
for p in periods1:
    for pay in p.payments:
        print(str(pay))

#print(round(calc_interest_payments(2012, periods1), 2))
#print(round(calc_interest_payments(2013, periods1), 2))