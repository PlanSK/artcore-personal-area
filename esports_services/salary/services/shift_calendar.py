import calendar


if __name__ == "__main__":
    month_calender = calendar.Calendar(firstweekday=0)

    for i in month_calender.monthdays2calendar(year=2022, month=7):
        print(i)