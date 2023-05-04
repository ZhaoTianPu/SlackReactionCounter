# Date parser
def parse_date(date):
    """Parse argument date to days, weeks, months, years"""
    days = 0
    weeks = 0
    months = 0
    years = 0

    last = 0
    for i, dchar in enumerate(date):
        if dchar == "d":
            days = int(date[last:i])
            last = i + 1
        elif dchar == "w":
            weeks = int(date[last:i])
            last = i + 1
        elif dchar == "m":
            months = int(date[last:i])
            last = i + 1
        elif dchar == "y":
            years = int(date[last:i])
            last = i + 1

    return days, weeks, months, years