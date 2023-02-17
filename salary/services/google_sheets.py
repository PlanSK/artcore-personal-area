import gspread
import logging
import datetime

from django.conf import settings
from django.core.cache import cache

from salary.services.db_orm_queries import get_users_full_names_list_from_db


logger = logging.getLogger(__name__)


def get_worksheet_name(year: int, month: int) -> str:
    """Returns formatted worksheet name 'mm-yyyy' 
    from year and month values for request.
    """
    return f'0{month}-{year}' if month < 10 else f'{month}-{year}'


def get_gsheets_worksheet_data(worksheet_name: str) -> list[list[str]]:
    """Connect to google sheets and return data from worksheet."""
    api_key: dict = settings.GSHEETS_API_KEY
    spreadsheet: str = settings.SPREADSHEET
    all_worksheet_data = []
    try:
        google_connect = gspread.service_account_from_dict(api_key)
        gsheet = google_connect.open_by_key(spreadsheet)
        worksheet = gsheet.worksheet(worksheet_name)
        all_worksheet_data = worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound as exception:
        logger.exception(f'Error access {worksheet_name}: {exception}')
    except (gspread.exceptions.GSpreadException,
            gspread.exceptions.UnSupportedExportFormat) as exception:
        logger.exception(
            f'Unknown gspread exception: {exception}')

    return all_worksheet_data


def _get_full_names_tuple(worksheet_data: list[list[str]]) -> tuple[str]:
    """Returns list with full names employees in worksheet."""
    first_cols_list = [row[0] for row in worksheet_data]
    names_list = get_users_full_names_list_from_db()

    full_names_tuple = tuple(
        full_employee_name
        for full_employee_name in names_list
        if full_employee_name in first_cols_list
    )
    return full_names_tuple


def _get_list_of_dates_from_int(row: list, month: int,
                                year: int) -> list[datetime.date]:
    """Returns list of dates from list of numbers of days."""
    workshift_symbol = settings.WORKSHIFT_SYMBOL
    workday_dates_list = []
    for number, value in enumerate(row):
        if workshift_symbol.upper() == value.upper().strip():
            try:
                workday_dates_list.append(datetime.date(year, month, number))
            except ValueError as exception:
                logger.warning(
                    f'Incorrect number of day in current number '
                    f'{number}: {exception}'
                )
    return workday_dates_list


def get_employees_schedule_dict(year: int, month: int) -> dict:
    """Returns dict with full names keys of employees,
    and List[datetime.date] as values. 
    List[datetime.date] contains dates with planed shifts.

    Returns:
        dict: { 'Full name': List[datetime.date] }
    """
    worksheet_name = get_worksheet_name(year, month)
    employees_schedule_dict = cache.get(worksheet_name)
    if employees_schedule_dict is None:
        worksheet_data = get_gsheets_worksheet_data(worksheet_name)
        full_names_tuple = _get_full_names_tuple(worksheet_data)
        employees_schedule_dict = {
            row[0].strip(): _get_list_of_dates_from_int(row, month, year)
            for row in worksheet_data
            if row[0].strip() in full_names_tuple
        }
        cache.set(worksheet_name, employees_schedule_dict,
                  settings.DEFAULT_CACHE_LIFETIME)
        logger.info(f'The worksheet {worksheet_name} is cached.')
    return employees_schedule_dict
