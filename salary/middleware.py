from django.shortcuts import render
from django.conf import settings


def maintrance_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if settings.MAINTRANCE_MODE:
            return render(request,
                          'salary/503.html',
                          {'title': 'Site in maintrance mode'})
        
        response = get_response(request)
        
        return response

        # Code to be executed for each request/response after
        # the view is called.

    return middleware