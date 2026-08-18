"CLI to interact with a remote Chaos server."

import base64
from http import HTTPStatus as HTTP
import json
import os
import sys

import click
import dotenv
import requests

# This must be done before importing 'constants'.
dotenv.load_dotenv()   # '.env' file exists only on the local machine.

import constants


class Data:
    def __init__(self, url=None, password=None, verbose=False):
        self.server = url.rstrip("/")
        self.password = password
        self.verbose = verbose

    def url(self, path):
        return f"{self.server}/api/{path or ''}"


@click.group("chaos")
@click.help_option("--help", "-h")
@click.option("--url", envvar="CHAOS_REMOTE_URL", help="URL of the Chaos server.")
@click.option(
    "--password", envvar="CHAOS_REMOTE_PASSWORD", help="Password for the Chaos server."
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.pass_context
def main(ctx, url, password, verbose):
    "CLI to interact with a remote Chaos server."
    ctx.obj = Data(url, password, verbose)


@main.command(help="Status of the server.")
@click.pass_obj
def status(obj):
    data = get(obj, "status")
    click.echo(f"Version {constants.__version__}")
    click.echo(f"{obj.server}/ (version {data.get('version', '?')})")
    click.echo(f"{data['ram']} memory used")
    click.echo(f"{data['disk_usage']} disk used")
    click.echo(f"{data['disk_free']} disk free")
    click.echo(f"{data['items_count']} entries")
    click.echo(f"{data['trash_count']} trash items")
    click.echo(f"{data['trash_usage']} trash size")


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
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option("--text", **text_args)
@click.pass_obj
def note(obj, title, tags, text):
    response = post(obj, "note", get_data(obj, title, tags, text))
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add a link.")
@click.option("--title", **title_args)
@click.option("--href", prompt=True, help="Href for the link.")
@click.option("--tags", **tags_args)
@click.option("--text", **text_args)
@click.pass_obj
def link(obj, title, href, tags, text):
    response = post(obj, "link", get_data(obj, title, tags, text, href=href))
    click.echo(f"Added {obj.server}{response['url']}")


@main.command(help="Add an image file.")
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
    response = post(
        obj,
        "image",
        get_data(
            obj,
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
    response = post(
        obj,
        "file",
        get_data(
            obj,
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
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option("--color", prompt=True, default="", help="Color of tag; hex or name.")
@click.option("--text", **text_args)
@click.pass_obj
def tag(obj, title, tags, color, text):
    response = post(obj, "tag", get_data(obj, title, tags, text, color=color or None))
    click.echo(f"Added {obj.server}{response['url']}")


def get(obj, path=None):
    "Server GET call."
    response = requests.get(obj.url(path), headers=dict(password=obj.password))
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        sys.exit(f"Error: {response.status_code=}")
    elif response.status_code == HTTP.NOT_FOUND:
        sys.exit(f"Error: no such URL '{response.url}'")
    elif response.status_code != HTTP.OK:
        sys.exit(f"Error: {response.status_code=} {response.content=}")
    return response.json()


def post(obj, path, data):
    "Server POST call."
    response = requests.post(
        obj.url(path), headers=dict(password=obj.password), data=json.dumps(data)
    )
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        sys.exit(f"Error: {response.status_code=}")
    elif response.status_code == HTTP.NOT_FOUND:
        sys.exit(f"Error: no such URL '{response.url}'")
    elif response.status_code != HTTP.OK:
        sys.exit(f"Error: {response.status_code=} {response.content=}")
    return response.json()


def get_data(obj, title, tags, text, **kwargs):
    "Return the dictionary for a POST call to add an item."
    result = {"title": title}
    if tags:
        result["tags"] = get_tags(obj, tags.split())
    else:
        result["tags"] = None
    if text.casefold() == "e":
        result["text"] = click.edit()
    else:
        result["text"] = text
    result.update(kwargs)
    return result


def get_tags(obj, given_tags):
    "Interpret the given tags in terms of actually existing tags."
    # Get tags defined on the server.
    existing_tags = get(obj, "tags")
    ambiguous = set()
    unknown = set()
    result = []
    for tag in given_tags:
        candidates = []
        for id, title in existing_tags.items():
            if title.startswith(tag):
                candidates.append(id)
                break
            elif title.casefold().startswith(tag):
                candidates.append(id)
                break
        else:
            unknown.add(tag)
        if len(candidates) == 1:
            result.append(candidates[0])
        else:
            ambiguous.add(tag)
    if obj.verbose:
        click.echo(
            f"Tags: {', '.join(sorted(result, key=lambda i: i.casefold())) or '-'}"
        )
    if ambiguous:
        click.echo(
            f"Ignored ambiguous tags: {', '.join(sorted(ambiguous, key=lambda i: i.casefold()))}"
        )
    if unknown:
        click.echo(
            f"Ignored unknown tags: {', '.join(sorted(unknown, key=lambda i: i.casefold()))}"
        )
    return result or None


if __name__ == "__main__":
    main()
