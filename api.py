"API resources."

from http import HTTPStatus as HTTP
import io
import tarfile

from fasthtml.common import *

import components
import constants
import entries
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
    "Return a JSON dictionary of items {name: modified} for all entries."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return entries.get_all()


@rt("/keywords")
def get(request):
    "Return a JSON dictionary containing the keywords."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return settings.keywords


@rt("/keyword/{keyword}")
def get(request, keyword: str):
    """Return a JSON dictionary of items {name: filename}, where 'filename'
    may be None, for all entries with the given keyword.
    """
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    result = {}
    for entry in entries.get_keyword_entries(keyword):
        try:
            result[str(entry)] = entry.filename
        except AttributeError:
            result[str(entry)] = None
    return result


@rt("/process/{process}")
def get(request, process: str):
    """Return a JSON dictionary of items {name: filename}, where 'filename'
    may be None, for all entries with the given process request.
    """
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    result = {}
    for entry in entries.get_process_entries(process):
        try:
            result[str(entry)] = entry.filename
        except AttributeError:
            result[str(entry)] = None
    return result


@rt("/entry/{entry:Entry}")
def get(request, entry: entries.Entry):
    "Return the text contents of an entry."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    return {"frontmatter": entry.frontmatter, "text": entry.text}


@rt("/entry/{entry:Entry}")
def post(request, entry: entries.Entry, text: str = None, process: str = None):
    "Set the text of an entry, optionally removing a process request."
    try:
        check_apikey(request)
    except KeyError as error:
        return Response(content=str(error), status_code=HTTP.UNAUTHORIZED)
    if text is not None:
        entry.text = text.strip()
    if process and process == entry.frontmatter.get("process"):
        entry.frontmatter.pop("process")
    entry.write()
    entries.set_keywords_relations(entry)
    return Response(content="text updated", status_code=HTTP.OK)


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
        for name in data["entries"]:
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
