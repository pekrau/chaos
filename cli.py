"""Command line interface to interact with a Chaos server.
NOTE: This uses its own virtual environment, as specified in 'cli_requirements.txt'.
"""

import base64
from http import HTTPStatus as HTTP
import json
import mimetypes
import os
import sys

import click
import dotenv
import requests

# This must be done before importing 'constants'.
dotenv.load_dotenv()  # '.env' file exists only on the local machine.

import constants
from timer import Timer
import utils


class Interface:
    "URL, password, get, post and timer."

    def __init__(self, url, password):
        self.server = url.rstrip("/")
        self.password = password
        self.timer = Timer()

    def url(self, path):
        if path is None:
            return f"{self.server}/api/"
        elif path.startswith("/"):
            return f"{self.server}{path}"
        else:
            return f"{self.server}/api/{path}"

    @property
    def headers(self):
        return dict(password=self.password)

    def get(self, path=None, as_text=False):
        "GET call to the server. Return the data as JSON or text."
        response = requests.get(self.url(path), headers=self.headers)
        if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
            sys.exit(f"Error: {response.status_code=}")
        elif response.status_code == HTTP.NOT_FOUND:
            sys.exit(f"Error: no such URL '{response.url}'")
        elif response.status_code != HTTP.OK:
            sys.exit(f"Error: {response.status_code=} {response.content=}")
        if as_text:
            return response.text
        else:
            return response.json()

    def post(self, path, data):
        "POST call to the server. Return the JSON data."
        response = requests.post(
            self.url(path), headers=self.headers, data=json.dumps(data)
        )
        if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
            sys.exit(f"Error: {response.status_code=}")
        elif response.status_code == HTTP.NOT_FOUND:
            sys.exit(f"Error: no such URL '{response.url}'")
        elif response.status_code != HTTP.OK:
            sys.exit(f"Error: {response.status_code=} {response.content=}")
        return response.json()

    def data(self, title, tags, text, **kwargs):
        "Return the dictionary for a POST call to add an item."
        result = {"title": title}
        if tags:
            result["tags"] = self.get_tags(tags.split())
        else:
            result["tags"] = None
        if text.casefold() == "e":
            result["text"] = click.edit()
        else:
            result["text"] = text
        result.update(kwargs)
        return result

    def get_tags(self, given_tags):
        "Interpret the given tags in terms of actually existing tags."
        # Get tags defined on the server.
        existing_tags = self.get("tags")
        ambiguous = set()
        unknown = set()
        result = []
        for tag in given_tags:
            candidates = []
            for id, title in existing_tags.items():
                if title.startswith(tag):
                    candidates.append(id)
                elif title.casefold().startswith(tag):
                    candidates.append(id)
            if len(candidates) == 1:
                result.append(candidates[0])
            elif len(candidates) > 0:
                ambiguous.add(tag)
            else:
                unknown.add(tag)
        if ambiguous:
            click.echo(
                f"Ignoring ambiguous tags: {', '.join(sorted(ambiguous, key=lambda i: i.casefold()))}"
            )
        if unknown:
            click.echo(
                f"Ignoring unknown tags: {', '.join(sorted(unknown, key=lambda i: i.casefold()))}"
            )
        return result or None


@click.group("chaos")
@click.help_option("--help", "-h")
@click.option("--url", envvar="CHAOS_REMOTE_URL", help="URL of the Chaos server.")
@click.option(
    "--password", envvar="CHAOS_REMOTE_PASSWORD", help="Password for the Chaos server."
)
@click.pass_context
def main(ctx, url, password):
    "CLI to interact with a Chaos server."
    ctx.obj = Interface(url, password)


@main.command(help="Status of the server.")
@click.help_option("--help", "-h")
@click.pass_obj
def status(obj):
    data = obj.get("status")
    resources = data["resources"]
    click.echo(f"Version {constants.__version__}")
    click.echo(f"{obj.server}/ (version {data.get('version', '?')})")
    click.echo(f"{resources['ram_used']:16_d} RAM used")
    click.echo(f"{resources['ram_total']:16_d} RAM total")
    click.echo(f"{resources['disk_data']:16_d} disk used")
    click.echo(f"{resources['disk_total']:16_d} disk total")
    click.echo(f"{resources['items_count']:16_d} entries")
    click.echo(f"{resources['trash_count']:16_d} trash # items")
    click.echo(f"{resources['trash_used']:16_d} trash data")


title_args = dict(type=str, prompt=True)
tags_args = dict(
    prompt=True,
    default="",
    help="Multiple on the same line; unique abbreviations allowed.",
)
text_args = dict(
    prompt="text ('e' for editor)",
    default="",
    help="Type 'e' for an editor.",
)


@main.command(help="Add a note.")
@click.help_option("--help", "-h")
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option("--text", **text_args)
@click.pass_obj
def note(obj, title, tags, text):
    response = obj.post("note", obj.data(title, tags, text))
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add a link.")
@click.help_option("--help", "-h")
@click.option("--title", **title_args)
@click.option("--href", prompt=True, help="Href for the link.")
@click.option("--tags", **tags_args)
@click.option("--text", **text_args)
@click.pass_obj
def link(obj, title, href, tags, text):
    response = obj.post("link", obj.data(title, tags, text, href=href))
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add an image file.")
@click.help_option("--help", "-h")
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option(
    "--file",
    prompt=True,
    type=click.File("rb"),
    help="Image file (PNG, JPEG, SVG, WEBP or GIF).",
)
@click.option("--text", **text_args)
@click.pass_obj
def image(obj, title, tags, file, text):
    response = obj.post(
        "image",
        obj.data(
            title,
            tags,
            text,
            file=dict(
                name=file.name,
                content=base64.b64encode(file.read()).decode("ascii"),
                encoding="base64",
            ),
        ),
    )
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add a file.")
@click.help_option("--help", "-h")
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option(
    "--file",
    prompt=True,
    type=click.File("rb"),
    help="File; any format except Markdown.",
)
@click.option("--text", **text_args)
@click.pass_obj
def file(obj, title, tags, file, text):
    response = obj.post(
        "file",
        obj.data(
            title,
            tags,
            text,
            file=dict(
                name=file.name,
                content=base64.b64encode(file.read()).decode("ascii"),
                encoding="base64",
            ),
        ),
    )
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add a tag.")
@click.help_option("--help", "-h")
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option("--color", prompt=True, default="", help="Color of tag; hex or name.")
@click.option("--text", **text_args)
@click.pass_obj
def tag(obj, title, tags, color, text):
    response = obj.post("tag", obj.data(title, tags, text, color=color or None))
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Optical Character Recognition of an image")
@click.help_option("--help", "-h")
@click.option("--language", "-l", type=str, default="en", help="Language for text.")
@click.option(
    "--upload",
    type=bool,
    flag_value=True,
    default=False,
    help="Upload the text to the item.",
)
@click.argument("itemid", type=str, required=True, help="Item identifier.")
@click.pass_obj
def ocr(obj, language, upload, itemid):
    itemid = itemid.lstrip("[[").rstrip("]]")
    frontmatter, text = utils.split_markdown(obj.get(f"item/{itemid}", as_text=True))
    if frontmatter.get("type") != "image" or not (ext := frontmatter.get("ext")):
        sys.exit("Error: Item is not an image.")
    if mimetypes.guess_type(f"dummy{ext}")[0] not in constants.PIXEL_IMAGE_MIMETYPES:
        sys.exit("Error: Item is not a pixel image.")
    response = requests.get(obj.url(f"/image/{itemid}{ext}"), headers=obj.headers)
    click.echo(f"Before importing EasyOCR: {obj.timer}")
    import easyocr

    click.echo(f"After importing EasyOCR: {obj.timer}")
    reader = easyocr.Reader([language], gpu=False, verbose=False)
    click.echo(f"After loading EasyOCR '{language}': {obj.timer}")
    result = reader.readtext(response.content, detail=0)
    click.echo(f"After detecting text: {obj.timer}")
    if result:
        result = "\n".join(result)
        click.echo(result)
        if upload:
            text += "\n\n" + result
            obj.post(f"item/{itemid}", data=dict(frontmatter=frontmatter, text=text))
            click.echo("Result uploaded.")
    else:
        click.echo("<No text found>")


if __name__ == "__main__":
    main()
