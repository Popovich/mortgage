# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
import calendar
from itertools import islice
import math
from decimal import Decimal
from collections import defaultdict
from copy import deepcopy

class Payment(object):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal):
        self.date = date
        self.payment = payment
        self.interest_payment = interest_payment
        self.principal_payment = principal_payment
        self.current_principal = current_principal
        self.not_used = False

class RegularPayment(Payment):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal):
        return super().__init__(date, payment, interest_payment, principal_payment, current_principal)

    def __str__(self):
        if not self.not_used:
            return '%s - %.2f - %.2f - %.2f - %.2f - regular' % (str(self.date), self.payment, self.interest_payment, self.principal_payment, self.current_principal)
        else:
            return '%s - %.2f - not used' % (str(self.date), self.payment) 

class NonRegularPayment(Payment):
    def __init__(self, date, payment, interest_payment, principal_payment, current_principal):
        super().__init__(date, payment, interest_payment, principal_payment, current_principal)

    def __str__(self):
        if not self.not_used:
            return '%s - %.2f - %.2f - %.2f - %.2f - non regular' % (str(self.date), self.payment, self.interest_payment, self.principal_payment, self.current_principal)
        else:
            return '%s - %.2f - not used' % (str(self.date), self.payment) 

class Period(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.payments = []
        self.principal_paid = False

    def add_payment(self, payment):
        self.payments.append(payment)

class Result(object):
    def __init__(self):
        self.payments = defaultdict(list)
        self.year_interest_payments = defaultdict(Decimal)

class Mortgage(object):
    def __init__(self, principal, interest, months, start_date):
        self.principal = principal
        self.interest = interest
        self.interest_rate = Decimal(interest / 100)
        self.monthly_interest = Decimal(self.interest_rate / 12)

        # срок кредита
        self.total_months = months

        self.initial_monthly_payment = self.calc_monthly_payment(self.principal, self.total_months)

        # дата получения кредита
        self.start_date = start_date

        self.cached_calendar = [self.start_date + relativedelta(months=m) for m in range(0, self.total_months + 1)]

        self.leap_years_cache = [366 if calendar.isleap(self.start_date.year + y) else 365 for y in range(0, int(self.total_months / 12))]

    # посчитать ежемесячный платёж
    def calc_monthly_payment(self, principal, months):
        return Decimal(round(principal * (self.monthly_interest / (1 - (1 + self.monthly_interest) ** (- months))), 2))

    # посчитать проценты за указанный период для указанной суммы долга
    def calc_interest_payment(self, pay_date, prev_pay_date, principal):
        # первый месяц в году, т.е. январь
        # в этом случае надо немного по-другому считать
        days_in_year = self.leap_years_cache[self.start_date.year - pay_date.year]
        if pay_date.month == 1 and prev_pay_date.month == 12:
            december31 = datetime.date(prev_pay_date.year, 12, 31)
        
            days1 = december31 - prev_pay_date
            days1 = days1.days
            p1 = Decimal(days1 / self.leap_years_cache[self.start_date.year - prev_pay_date.year])
            interest_payment1 = Decimal(round(principal * self.interest_rate * p1, 2))
        
            days2 = pay_date - december31
            days2 = days2.days
            p2 = Decimal(days2 / days_in_year)
            interest_payment2 = Decimal(round(principal * self.interest_rate * p2, 2))
        
            return interest_payment1 + interest_payment2
        else:
            d = pay_date - prev_pay_date
            days = d.days
        
            return Decimal(round(principal * self.interest_rate * days / days_in_year, 2))

    def is_pay_in_regular_date(self, pay):
        return pay.date.day == self.start_date.day

    def calc(self, predefined_payments = {}, initial_month = None):
        current_principal = self.principal
        monthly_payment = self.calc_monthly_payment(current_principal, self.total_months)

        result = Result()
        cur_period = self.cached_calendar[0 if initial_month == None else initial_month]

        for m in range(1 if initial_month == None else initial_month + 1, self.total_months + 1):
            end_period = self.cached_calendar[m]
            principal_paid = False

            non_reg_payments = predefined_payments.get((end_period.year, end_period.month), [])
            for non_reg_pay in non_reg_payments:
                if self.is_pay_in_regular_date(non_reg_pay):

                    if current_principal <= non_reg_pay.payment: # хотим заплатить больше, чем должны. скорректируем
                        non_reg_pay.payment = current_principal
                    current_principal -= non_reg_pay.payment

                    non_reg_pay.current_principal = current_principal
                    non_reg_pay.principal_payment = non_reg_pay.payment
                    non_reg_pay.interest_payment = 0
                    result.payments[non_reg_pay.date].append(non_reg_pay)

                    if current_principal == 0:
                        break

                    # так как долг поменялся, пересчитаем аннуитентный платёж
                    left_months = self.total_months - m + 1 # сколько месяцев осталось платить
                    monthly_payment = self.calc_monthly_payment(current_principal, left_months)
                else:
                    # считаем набежавшие проценты от последнего платежа до даты досрочки
                    p = self.calc_interest_payment(non_reg_pay.date, cur_period, current_principal)
                    result.year_interest_payments[non_reg_pay.date.year] += p

                    if non_reg_pay.payment < p:
                        non_reg_pay.not_used = True
                        result.payments[non_reg_pay.date].append(non_reg_pay)
                        pass # не хватает для выплаты процентов
                    else:
                        # обновим остаток долга с учётом процентов

                        if current_principal <= non_reg_pay.payment - p: # хотим заплатить больше, чем должны. скорректируем
                            non_reg_pay.payment = current_principal + p
                        current_principal -= non_reg_pay.payment - p

                        # обновим инфу о платеже и добавим её в список платежей
                        non_reg_pay.interest_payment = p
                        non_reg_pay.current_principal = current_principal
                        non_reg_pay.principal_payment = non_reg_pay.payment - p

                        principal_paid = True # в этом периоде больше за основной долг не платим
                        result.payments[non_reg_pay.date].append(non_reg_pay)

                        if current_principal == 0:
                            break

                        # так как долг поменялся, пересчитаем аннуитентный платёж
                        left_months = self.total_months - m # сколько месяцев осталось платить
                        monthly_payment = self.calc_monthly_payment(current_principal, left_months)

                        cur_period = non_reg_pay.date
    
            if current_principal == 0:
                break

            # регулярный платёж
            interest_payment = self.calc_interest_payment(end_period, cur_period, current_principal)
            result.year_interest_payments[end_period.year] += interest_payment

            if m == self.total_months and monthly_payment > current_principal: # last payment
                principal_payment = current_principal
                monthly_payment = interest_payment + principal_payment
            elif not principal_paid:
                principal_payment = monthly_payment - interest_payment
            else:
                principal_payment = 0

            current_principal -= principal_payment

            payment = RegularPayment(end_period, interest_payment + principal_payment, interest_payment, principal_payment, current_principal)
            principal_paid = True
            result.payments[payment.date].append(payment)

            if current_principal == 0:
                break

            cur_period = end_period

        return result


def make_non_reg_payment(year, month, day, sum):
    return NonRegularPayment(datetime.date(year, month, day), Decimal(round(sum, 2)), 0, 0, 0)

def add_non_reg_payment(payments, reg_pay_day, year, month, day, sum):
    if day < reg_pay_day:
        t = (year, month)
    else:
        d = datetime.date(year, month, 1)
        d += relativedelta(months=1)
        t = (d.year, d.month)
    payments[t].append(make_non_reg_payment(year, month, day, sum))

def calc_interest_payments(year, periods):
    s = 0
    for p in periods:
        if p.end.year == year:
            for pay in p.payments:
                s += pay.interest_payment

    return s

def diff_dates(dt1, dt2):
    diff = relativedelta(dt1, dt2)
    return diff.years * 12 + diff.months

# каждый месяц добавляем в досрочку разницу между текущим ежемесячным платежём и первоначальным
def calc_auto_4dp_v1(mortgage, non_reg_payments, next_pay_date, stop_date=None):

    initial_monthly_payment = mortgage.initial_monthly_payment

    result = None
    while True:
        result = mortgage.calc(non_reg_payments)
        date, delta = sim_auto_4dp(initial_monthly_payment, result.payments, next_pay_date)
        if date is None:
            break

        non_reg_payments[(date.year, date.month)].append(NonRegularPayment(next_pay_date, delta, 0, 0, 0))

        next_pay_date = date

        if next_pay_date == stop_date:
            break

    return result

def sim_auto_4dp(initial_monthly_payment, payments, start_date):

    pays = payments.get(start_date, [])
    for pay in pays:
        if isinstance(pay, RegularPayment):
            delta = initial_monthly_payment - pay.payment # разница между изначальным платежом и сколько теперь платим
            if delta == 0:
                return None, None
            delta = math.ceil(delta / 1000) * 1000 # округлим до тысячи в большую сторону
            if delta > pay.current_principal: # осталось заплатить меньше, чем получившаяся разница
                delta = pay.current_principal
            next_pay_date = pay.date + relativedelta(months=1) # следующий платёж + 1 месяц
            return next_pay_date, delta
    return None, None

# второй вариант ЧДП
# вносим платежи два раза за расчётный период (i-го числа ЧДП и 18-го числа всё что осталось)
def calc_auto_4dp_v2(mortgage, non_reg_payments, next_pay_date, day, boost):

    if next_pay_date.day != mortgage.start_date.day:
        raise RuntimeError("next_pay_date.day != mortgage.start_date.day")

    while True:
        r = calc_auto_4dp_v1(mortgage, non_reg_payments, next_pay_date, next_pay_date + relativedelta(months=2))

        last_pay_date = next_pay_date - relativedelta(months=1)
        last_pay = r.payments.get(last_pay_date, [None])[0]
        if not last_pay:
            return r

        pays = r.payments.get(next_pay_date, [])
        regular = pays[0]
        if boost and len(pays) > 1:
            non_regular = r.payments.get(next_pay_date, [])[1]
            non_regular_principal_payment = non_regular.principal_payment
        else:
            non_regular_principal_payment = Decimal(0.0)

        old_total_payment = regular.principal_payment + regular.interest_payment + non_regular_principal_payment
        old_total_principal_payment = regular.principal_payment + non_regular_principal_payment

        new_pay_date = next_pay_date - relativedelta(months=1)
        new_pay_date = datetime.date(new_pay_date.year, new_pay_date.month, day) # первый платёж в этом периоде

        diff = Decimal(0.0)
        while True:

            cur_total_principal_payment = old_total_principal_payment + diff

            # проценты с 18-го по i-е
            interest_p1 = mortgage.calc_interest_payment(new_pay_date, last_pay_date, last_pay.current_principal)
            principal_p1 = cur_total_principal_payment
            new_total_payment_1 = interest_p1 + principal_p1

            # проценты с i-го по 18-ое след месяца
            interest_p2 = mortgage.calc_interest_payment(regular.date, new_pay_date, last_pay.current_principal - principal_p1)
            principal_p2 = 0
            new_total_payment_2 = interest_p2 + principal_p2

            new_total_payment = new_total_payment_1 + new_total_payment_2

            if new_total_payment < old_total_payment:
                diff += old_total_payment - new_total_payment
                continue

            break

        add_non_reg_payment(non_reg_payments, mortgage.start_date.day, new_pay_date.year, new_pay_date.month, new_pay_date.day, interest_p1 + principal_p1)

        c = regular.date + relativedelta(months=1)
        if non_reg_payments.get((c.year, c.month), None):
            del non_reg_payments[(c.year, c.month)]

        next_pay_date += relativedelta(months=1)

def get_payments_info(payments):
    s1 = 0 # сколько уплатим банку по процентам
    payments = sorted(payments.items())
    for k, v in payments:
        for p in v:
            s1 += p.interest_payment

    return s1, payments[-1][0]

def print_payments(payments):
    s1 = 0 # сколько уплатим банку по процентам
    for k, v in sorted(payments.items()):
        for p in v:
            s1 += p.interest_payment
            print(p)
    print("Total interest payment: %s - %% = %s" % (s1, round(s1*Decimal("0.13"), 2)))

def get_auto_4dp_start_date(mortgage, non_reg_payments):

    max = (0, 0)
    for p in non_reg_payments.keys():
        if p > max:
            max = p

    return datetime.date(max[0], max[1], m.start_date.day) + relativedelta(months=1)

if __name__ == '__main__':

    m = Mortgage(principal=4900000, interest=12.4, months=12*20, start_date=datetime.date(2012, 4, 18))

    # уже совершённые ЧДП
    non_reg_payments = defaultdict(list)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 1, 15, 800000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 2, 18, 10000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 3, 18, 80000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 4, 18, 16000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 6, 9,  130000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 6, 14, Decimal(51182.53))
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 8, 18, 15000)
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 9, 16, Decimal(55798.25))
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 9, 26, Decimal(29687.71))
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 10, 26, Decimal(15367.83))
    add_non_reg_payment(non_reg_payments, m.start_date.day, 2016, 11, 25, Decimal(15429.54))

    # more to come

    auto_4dp_start_date = datetime.date(2017, 2, 18) #get_auto_4dp_start_date(m, non_reg_payments) # дата, с которой начинаем авто ЧДП

    # classic
    r1 = m.calc(deepcopy(non_reg_payments))
    print("Total interest payment (classic): %s (%s)" % get_payments_info(r1.payments))

    # 4dp v1
    r2 = calc_auto_4dp_v1(m, deepcopy(non_reg_payments), next_pay_date=auto_4dp_start_date)
    print("Total interest payment (4dp v1): %s (%s)" % get_payments_info(r2.payments))

    # 4dp v2 boost=False
    r3 = calc_auto_4dp_v2(m, deepcopy(non_reg_payments), next_pay_date=auto_4dp_start_date, day=25, boost=False)
    print("Total interest payment (4dp v2 no boost 25): %s (%s)" % get_payments_info(r3.payments))

    # 4dp v2 boost=True
    r4 = calc_auto_4dp_v2(m, deepcopy(non_reg_payments), next_pay_date=auto_4dp_start_date, day=25, boost=True)
    print("Total interest payment (4dp v2 boost 25): %s (%s)" % get_payments_info(r4.payments))

    # 4dp v2 boost=False

    r5 = calc_auto_4dp_v2(m, deepcopy(non_reg_payments), next_pay_date=auto_4dp_start_date, day=26, boost=False)
    print("Total interest payment (4dp v2 no boost 26): %s (%s)" % get_payments_info(r5.payments))

    # 4dp v2 boost=True
    r6 = calc_auto_4dp_v2(m, deepcopy(non_reg_payments), next_pay_date=auto_4dp_start_date, day=26, boost=True)
    print("Total interest payment (4dp v2 boost 26): %s (%s)" % get_payments_info(r6.payments))

    #print_payments(r.payments)
    #print("Interest payments by years:")
    #for k, v in sorted(r.year_interest_payments.items()):
    #    print("%s - %s - %% = %s" % (k, v, round(v * Decimal("0.13"), 2)))