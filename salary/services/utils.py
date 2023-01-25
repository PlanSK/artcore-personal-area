import logging
import sys
import time
import traceback

from functools import wraps
from typing import Callable, Any

from django.core import mail
from django.http import HttpRequest
from django.views.debug import ExceptionReporter


logger = logging.getLogger(__name__)


def execution_time_log(function: Callable) -> Any:
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        func = function(*args, **kwargs)
        logger.info(f'{function.__name__}: {round(time.monotonic()-start, 3)}s')
        return func
    return wrapper


def logging_exception(request: HttpRequest, exception: Exception) -> None:
    """
    Logging exception as critical error
    """
    logger.critical(traceback.format_exc())


def manual_send_traceback(request: HttpRequest, exception: Exception) -> None:
    """
    Send mail to admins with traceback
    """
    exc_info = sys.exc_info()
    reporter = ExceptionReporter(request, is_email=True, *exc_info)
    subject = f'CRITICAL ERROR: {exception}'
    message = reporter.get_traceback_text()
    mail.mail_admins(subject, message, fail_silently=True)
