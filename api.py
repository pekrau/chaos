"API resources."

from http import HTTPStatus as HTTP
import io
import tarfile

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Return a JSON dictionary of items {name: modified} for all items."
    return items.get_all_files()


@rt("/item/{item:Item}")
def get(request, item: items.Item):
    "Return the Markdown contents of an item."
    return {"frontmatter": item.frontmatter, "text": item.text}


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
