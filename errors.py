"Errors and handlers."

from http import HTTPStatus as HTTP

from fasthtml.common import *


class Error(Exception):
    "Custom exception; return response with message and status code."

    def __init__(self, message, status_code=HTTP.BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


def error_handler(request, exc):
    "Return a response with the message and status code."
    return Response(content=str(exc), status_code=exc.status_code)
