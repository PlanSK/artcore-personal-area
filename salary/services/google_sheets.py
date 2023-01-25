import gspread
import logging

from typing import List, Tuple

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.db.models import QuerySet


logger = logging.getLogger(__name__)


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


def get_full_names_tuple(worksheet_data: List[List[str]],
                        full_names_from_db: QuerySet) -> Tuple[str]:
    """
    Returns list with full names employees in worksheet.
    """
    first_cols_list = [row[0] for row in worksheet_data]

    full_names_tuple = tuple(
        user_instance.get_full_name()
        for user_instance in full_names_from_db
        if user_instance.get_full_name() in first_cols_list
    )

    return full_names_tuple


def get_worksheet_name(year: int, month: int) -> str:
    """
    Returns str with google worksheet name

    Args:
        year (int): requested year
        month (int): requested month

    Returns:
        str: worksheet name, 'mm-yyyy'
    """
    if month < 10:
        return f'0{month}-{year}'
    
    return f'{month}-{year}'


def get_employees_schedule_dict(year: int, month: int) -> dict:
    """
    Returns dict with full names keys of employees, and List[int] as values.
    List[int] contains number of day with planed shifts.

    Returns:
        dict: { 'FullName': List[int] }
    """

    worksheet_name = get_worksheet_name(year, month)
    employees_schedule_dict = cache.get(worksheet_name)

    if not employees_schedule_dict:
        worksheet_data = get_gsheets_worksheet_data(worksheet_name)
        full_names_from_db = User.objects.select_related('profile').exclude(
            profile__profile_status='DSM'
        )
        full_names_tuple = get_full_names_tuple(worksheet_data,
                                              full_names_from_db)
        employees_schedule_dict = {}
        days_numbers_list = []

        for employee_full_name in full_names_tuple:
            for row in worksheet_data:
                if employee_full_name == row[0]:
                    for number, value in enumerate(row):
                        if value == 'Р':
                            days_numbers_list.append(number)
            employees_schedule_dict.update({
                employee_full_name: days_numbers_list.copy()
            })
            days_numbers_list.clear()

        logger.info(f'Caching worksheet {worksheet_name}.')
        cache.set(worksheet_name, employees_schedule_dict,
                  settings.DEFAULT_CACHE_LIFETIME)

    return employees_schedule_dict
