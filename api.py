"API resources."

from http import HTTPStatus as HTTP
import io
import tarfile

from fasthtml.common import *

import components
import constants
import items
import utils

app, rt = components.get_app_rt()


@rt("/status")
def get():
    "Return status of the server."
    return utils.get_status()


@rt("/all")
def get():
    """Return a JSON dictionary of items {name: {modified, size}} for all items,
    which includes Markdown files and all other files (PDF, PNG, etc).
    """
    return items.get_all_files()


@rt("/tags")
def get():
    "Return the dictionary of all available tags; id -> title"
    return dict([(t.id, t.title) for t in items.get_items("tag")])


@rt("/note")
async def post(request):
    "Create and add a note."
    data = await request.json()
    note = items.Note()
    note.title = data["title"]
    note.tags = data["tags"]
    note.text = data["text"]
    note.write()
    return {"note": note.id, "url": note.url}


@rt("/tag")
async def post(request):
    "Create and add a tag."
    data = await request.json()
    tag = items.Tag()
    tag.title = data["title"]
    tag.tags = data["tags"]
    tag.text = data["text"]
    tag.write()
    return {"tag": tag.id, "url": tag.url}


@rt("/download")
async def post(request):
    "Return a TGZ file of those items named in the request JSON data."
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
