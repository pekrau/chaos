"API resources."

import base64
from http import HTTPStatus as HTTP
import io
import mimetypes
import pathlib
import tarfile

from fasthtml.common import *

import components
import constants
import errors
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


@rt("/link")
async def post(request):
    "Create and add a link."
    data = await request.json()
    link = items.Link()
    link.title = data["title"]
    link.href = data["href"]
    link.tags = data["tags"]
    link.text = data["text"]
    link.write()
    return {"link": link.id, "url": link.url}


@rt("/image")
async def post(request):
    "Create and add an image."
    data = await request.json()
    image = items.Image()
    image.title = data["title"]
    type = mimetypes.guess_type(data["file"]["name"])[0]
    if type not in constants.IMAGE_MIMETYPES:
        raise errors.Error(f"Invalid file type '{type}'", HTTP.UNSUPPORTED_MEDIA_TYPE)
    image.ext = pathlib.Path(data["file"]["name"]).suffix
    image.tags = data["tags"]
    image.text = data["text"]
    image.content = base64.b64decode(data["file"]["content"].encode("ascii"))
    image.write()
    return {"image": image.id, "url": image.url}


@rt("/file")
async def post(request):
    "Create and add a file."
    data = await request.json()
    file = items.File()
    file.title = data["title"]
    filename = data["file"]["name"]
    type = mimetypes.guess_type(filename)[0]
    if type == constants.MARKDOWN_MIMETYPE:
        raise errors.Error("Upload of Markdown file is disallowed.")
    elif type in constants.IMAGE_MIMETYPES:
        raise errors.Error("Image file must be uploaded as 'image'.")
    file.ext = filename.suffix
    file.tags = data["tags"]
    file.text = data["text"]
    file.content = base64.b64decode(data["file"]["content"].encode("ascii"))
    file.write()
    return {"file": file.id, "url": file.url}


@rt("/tag")
async def post(request):
    "Create and add a tag."
    data = await request.json()
    tag = items.Tag()
    tag.title = data["title"]
    tag.tags = data["tags"]
    tag.text = data["text"]
    tag.color = data.get("color") or None
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
