"API resources."

import base64
from http import HTTPStatus as HTTP
import io
import mimetypes
import pathlib
import tarfile

from fasthtml.common import *
import bibtexparser
import click
import fasthtml
import marko
import mermaidx
import psutil
import requests
import webcolors
import yaml

import components
import constants
import errors
import items
import utils

app, rt = components.get_app_rt()


@rt("/status")
def get():
    "Return status of the server."
    return get_status()


def get_status():
    "Get the status of the instance: resources, item counts, software"
    import items

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(constants.DATA_DIR)
    resources = {
        "ram_used": ram.used,
        "ram_total": ram.total,
        "ram_free": ram.free,
        "ram_process": psutil.Process().memory_info().rss,
        # This sums sizes of all files, not just '.md' files.
        "disk_data": sum(
            [
                os.path.getsize(constants.DATA_DIR / filename)
                for filename in constants.DATA_DIR.iterdir()
            ]
        ),
        "disk_percent": disk.percent,
        "disk_total": disk.total,
        "disk_free": disk.free,
        "items_count": len(items.lookup),
        "trash_count": len(
            [
                filename
                for filename in constants.TRASH_DIR.iterdir()
                if not filename.suffix
            ]
        ),
        "trash_used": sum(
            [
                os.path.getsize(constants.TRASH_DIR / filename)
                for filename in constants.TRASH_DIR.iterdir()
            ]
        ),
    }
    resources["ram_percent"] = 100 * resources["ram_process"] / ram.total
    resources["disk_percent"] = 100 * resources["disk_data"] / disk.total
    software = [
        dict(name="chaos", href=constants.GITHUB_URL, version=constants.__version__),
        dict(
            name="Python",
            href="https://www.python.org/",
            version=".".join([str(v) for v in sys.version_info[0:3]]),
        ),
        dict(name="fastHTML", href="https://fastht.ml/", version=fasthtml.__version__),
        dict(
            name="Marko",
            href="https://marko-py.readthedocs.io/",
            version=marko.__version__,
        ),
        dict(
            name="PyYAML",
            href="https://pypi.org/project/PyYAML/",
            version=yaml.__version__,
        ),
        dict(
            name="BibtexParser",
            href="https://bibtexparser.readthedocs.io/en/main/",
            version=bibtexparser.__version__,
        ),
        dict(
            name="requests",
            href="https://requests.readthedocs.io/en/latest/",
            version=requests.__version__,
        ),
        dict(
            name="click",
            href="https://click.palletsprojects.com/en/stable/",
            version=click.__version__,
        ),
        dict(
            name="Vega-Lite",
            href="https://vega.github.io/vega-lite/",
            version="6.5",  # Must track the libraries spec in 'constants.py'
        ),
        dict(
            name="mermaidx",
            href="https://github.com/MohammadRaziei/mermaidx",
            version=mermaidx.__version__,
        ),
        dict(
            name="Mermaid",
            href="https://mermaid.ai/open-source/intro/",
            version="11.16.0",  # Depends on what's in mermaidx.
        ),
        dict(
            name="psutil",
            href="https://github.com/giampaolo/psutil",
            version=psutil.__version__,
        ),
        dict(
            name="webcolors",
            href="https://webcolors.readthedocs.io/en/stable/",
            version="25.10.0",
        ),
        dict(
            name="Tabulator",
            href="https://tabulator.info/",
            version="6.5.0",  # Must track the libraries spec in 'constants.py'
        ),
    ]
    return dict(
        version=constants.__version__,
        resources=resources,
        data_items=items.get_counts(),
        software=software,
    )


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
    return dict(type="note", id=note.id, url=note.url)


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
    return dict(type="link", id=link.id, url=link.url)


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
    return dict(type="image", id=image.id, url=image.url)


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
    return dict(type="file", id=file.id, url=file.url)


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
    return dict(type="tag", id=tag.id, url=tag.url)


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


@rt("/item/{item:Item}")
def get(item: items.Item):
    "Return the source Markdown with YAML frontmatter."
    return Response(content=item.path.read_text(), media_type=constants.TEXT_MIMETYPE)


@rt("/item/{item:Item}")
async def post(request, item: items.Item):
    "Upload source Markdown with YAML frontmatter."
    data = await request.json()
    try:
        frontmatter = data["frontmatter"]
        if frontmatter.get("type") != item.type:
            raise errors.Error(f"Item type change not allowed", HTTP.FORBIDDEN)
    except KeyError:
        frontmatter = item.frontmatter
    try:
        text = data["text"]
    except KeyError:
        text = item.text
    match item.type:
        case "file" | "image":
            if frontmatter.get("ext") != item.ext:
                raise errors.Error(f"Item 'ext' may not be changed", HTTP.FORBIDDEN)
    item.frontmatter = frontmatter
    item.text = text
    item.write()
    return dict(type="image", id=item.id, url=item.url)
