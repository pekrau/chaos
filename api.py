"API resources."

from http import HTTPStatus as HTTP
import io
import tarfile

from fasthtml.common import *
import requests

import components
import constants
import entries

app, rt = components.get_app_rt()


@rt("/current")
def get(request):
    apikey = request.headers.get("apikey")
    if not apikey:
        return Response("no API key", status_code=HTTP.UNAUTHORIZED)
    if apikey != os.environ.get("CHAOS_APIKEY"):
        return Response("invalid API key", status_code=HTTP.UNAUTHORIZED)
    return entries.get_current()


@rt("/fetch")
async def post(request):
    data = await request.json()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tgzfile:
        for name in data["entries"]:
            path = constants.DATA_DIR / name
            if not path.suffix:
                path = path.with_suffix(".md")
            tgzfile.add(path, arcname=path.name)
    return Response(
        content=buffer.getvalue(),
        media_type=constants.GZIP_CONTENT_TYPE,
    )
