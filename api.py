"API resources."

from http import HTTPStatus as HTTP
import io
import tarfile

from fasthtml.common import *

import components
import constants
import items
import settings

app, rt = components.get_app_rt()


def check_apikey(request):
    apikey = request.headers.get("apikey")
    if not apikey:
        raise KeyError("no API key")
    if apikey != os.environ.get("CHAOS_APIKEY"):
        raise KeyError("invalid API key")


@rt("/")
def get(request):
    "Return a JSON dictionary of items {name: modified} for all items."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return items.get_all()


@rt("/keywords")
def get(request):
    "Return a JSON dictionary containing the keywords."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return {"keywords": list(settings.keywords)}


@rt("/keyword/{keyword}")
def get(request, keyword: str):
    """Return a JSON dictionary of items {name: filename}, where 'filename'
    may be None, for all items with the given keyword.
    """
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    result = {}
    for item in items.get_keyword_items(keyword):
        try:
            result[item.id] = item.filename
        except AttributeError:
            result[item.id] = None
    return result


@rt("/item/{item:Item}")
def get(request, item: items.Item):
    "Return the text contents of an item."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return {"frontmatter": item.frontmatter, "text": item.text}


@rt("/download")
async def post(request):
    "Return a TGZ file of those items named in the request JSON data."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    data = await request.json()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tgzfile:
        for name in data["items"]:
            path = constants.DATA_DIR / name
            if not path.suffix:
                path = path.with_suffix(".md")
            try:
                tgzfile.add(path, arcname=path.name)
            except FileNotFoundError:
                pass
    return Response(
        content=buffer.getvalue(),
        media_type=constants.GZIP_MIMETYPE,
    )
