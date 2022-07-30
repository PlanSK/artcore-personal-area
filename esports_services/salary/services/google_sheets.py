from typing import List

import gspread
from django.conf import settings


def get_gsheets_worksheet_data(worksheet_name: str) -> List[List[str]]:
    """
    Connect to google sheets and return data from workshift

    Args:
        table_key (str): Table url decode string
        worksheet_name (str): Worksheet name

    Returns:
        list: list of list
    """

    api_key: dict = settings.GSHEETS_API_KEY
    spreadsheet: str = settings.SPREADSHEET
    google_connect = gspread.service_account_from_dict(api_key)
    gsheet = google_connect.open_by_key(spreadsheet)
    worksheet = gsheet.worksheet(worksheet_name)

    return worksheet.get_all_values()


def get_full_names_list(worksheet_data: List[List[str]]) -> List[str]:
    """
    Returns list with full names employees in worksheet.
    """
    first_cols_list = [row[0] for row in worksheet_data]

    is_names: bool = False
    full_names_list: list = []

    for col in first_cols_list:
        if not col:
            is_names = False

        if is_names:
            full_names_list.append(col)

        if col == 'Имя сотрудника':
            is_names = True

    return full_names_list


def get_employees_schedule_dict(worksheet_name: str) -> dict:
    """
    Returns dict with full names keys of employees, and List[int] as values.
    List[int] contains number of day with planed shifts.

    Returns:
        dict: { 'FullName': List[int] }
    """

    worksheet_data = get_gsheets_worksheet_data(worksheet_name)
    full_names_list = get_full_names_list(worksheet_data)

    employees_schedule_dict = {}
    days_numbers_list = []
    for employee_full_name in full_names_list:
        for row in worksheet_data:
            if employee_full_name == row[0]:
                for number, value in enumerate(row):
                    if value == 'Р':
                        days_numbers_list.append(number)
        employees_schedule_dict.update({
            employee_full_name: days_numbers_list.copy()
        })
        days_numbers_list.clear()

    return employees_schedule_dict
