import gspread
import logging
import datetime

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


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


def get_gsheets_worksheet_data(worksheet_name: str) -> list[list[str]]:
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
    all_worksheet_data = []
    try:
        worksheet = gsheet.worksheet(worksheet_name)
        all_worksheet_data = worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound as exception:
        logger.exception(f'Error access {worksheet_name}: {exception}')
    except Exception as exception:
        logger.exception(
            f'Unknown error on access to {worksheet_name}: {exception}')
    finally:
        return all_worksheet_data


def get_full_names_list_from_db() -> list[str]:
    """
    Returns list with full names from db
    """
    user_name_tuples_list = User.objects.all().values_list('last_name',
                                                           'first_name')
    user_full_names_list = [
        ' '.join(names_tuple) for names_tuple in user_name_tuples_list
    ]
    return user_full_names_list


def get_full_names_tuple(worksheet_data: list[list[str]]) -> tuple[str]:
    """
    Returns list with full names employees in worksheet.
    """
    first_cols_list = [row[0] for row in worksheet_data]
    names_list = get_full_names_list_from_db()

    full_names_tuple = tuple(
        full_employee_name
        for full_employee_name in names_list
        if full_employee_name in first_cols_list
    )

    return full_names_tuple


def get_employees_schedule_dict(year: int, month: int) -> dict:
    """
    Returns dict with full names keys of employees, and List[int] as values.
    List[int] contains number of day with planed shifts.

    Returns:
        dict: { 'FullName': List[int] }
    """
    workshift_symbol = 'Р'
    worksheet_name = get_worksheet_name(year, month)
    employees_schedule_dict = cache.get(worksheet_name)

    if not employees_schedule_dict:
        worksheet_data = get_gsheets_worksheet_data(worksheet_name)
        full_names_tuple = get_full_names_tuple(worksheet_data)
        employees_schedule_dict = {}

        for employee_full_name in full_names_tuple:
            for row in worksheet_data:
                if employee_full_name in row[0]:
                    workday_dates_list = [
                        datetime.date(year, month, number)
                        for number, value in enumerate(row)
                        if workshift_symbol.upper() == value.strip().upper()
                    ]
            if workday_dates_list:
                employees_schedule_dict.update({
                    employee_full_name: workday_dates_list
                })

        logger.info(f'Caching worksheet {worksheet_name}.')
        cache.set(worksheet_name, employees_schedule_dict,
                  settings.DEFAULT_CACHE_LIFETIME)

    return employees_schedule_dict
