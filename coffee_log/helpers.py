from datetime import datetime


def get_first_days_of_last_six_months():
    # Get the current date
    current_date = datetime.now()

    # Initialize an empty list to store the first days
    first_days = []

    # Loop to get the first day of the last 6 months including the current month
    for i in range(6):
        # Calculate the month and year
        month = (current_date.month - i - 1) % 12 + 1
        year = current_date.year + (current_date.month - i - 1) // 12

        # Get the first day of the month
        first_day = datetime(year, month, 1)

        # Append the first day to the list
        first_days.append(first_day)

    return first_days
