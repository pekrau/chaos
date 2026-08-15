"CLI to interact with a remote Chaos server."

from http import HTTPStatus as HTTP
import json
import os
import sys

import click
import requests

# This must be done before importing 'constants'.
from dotenv import load_dotenv

if os.environ.get("CHAOS_DEVELOPMENT"):
    import icecream

    icecream.install()
    with open(".env-development") as infile:
        load_dotenv(stream=infile)
else:
    load_dotenv()


class Data:
    def __init__(self, url=None, password=None):
        self.url = url.rstrip("/")
        self.password = password


@click.group("chaos")
@click.option("--url", envvar="CHAOS_REMOTE_URL", help="URL of the Chaos server.")
@click.option(
    "--password", envvar="CHAOS_PASSWORD", help="Password for the Chaos server."
)
@click.pass_context
def main(ctx, url, password):
    ctx.obj = Data(url, password)


@main.command(help="Status of the server.")
@click.pass_obj
def status(obj):
    data = get(obj, "status")
    click.echo(obj.url)
    click.echo(f"{data['ram']} memory used")
    click.echo(f"{data['disk_usage']} disk used")
    click.echo(f"{data['disk_free']} disk free")
    click.echo(f"{data['items_count']} entries")
    click.echo(f"{data['trash_count']} trash items")
    click.echo(f"{data['trash_usage']} trash size")


title_args = dict(type=str, prompt=True)
tags_args = dict(
    type=str,
    prompt=True,
    default="",
    help="Multiple on the same line; unique abbreviations allowed.",
)
text_args = dict(
    type=str,
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
    click.echo(post(obj, "note", get_data(obj, title, tags, text)))


@main.command(help="Add a tag.")
@click.option("--title", **title_args)
@click.option("--tags", **tags_args)
@click.option("--text", **text_args)
@click.pass_obj
def tag(obj, title, tags, text):
    click.echo(post(obj, "tag", get_data(obj, title, tags, text)))


def get(obj, path=None):
    "Server GET call."
    url = obj.url + "/api"
    if path:
        url += "/" + path
    response = requests.get(url, headers=dict(password=obj.password))
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        sys.exit(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        sys.exit(f"invalid response: {response.status_code=} {response.content=}")
    return response.json()


def post(obj, path, data):
    "Server POST call."
    url = f"{obj.url}/api/{path}"
    response = requests.post(
        url, headers=dict(password=obj.password), data=json.dumps(data)
    )
    if response.status_code in (HTTP.BAD_GATEWAY, HTTP.SERVICE_UNAVAILABLE):
        sys.exit(f"invalid response: {response.status_code=}")
    elif response.status_code != HTTP.OK:
        sys.exit(f"invalid response: {response.status_code=} {response.content=}")
    return response.json()


def get_data(obj, title, tags, text):
    "Return the dictionary for add item POST call."
    result = {"title": title}
    if tags:
        result["tags"] = get_tags(obj, tags.split())
    else:
        result["tags"] = None
    if text.casefold() == "e":
        result["text"] = click.edit()
    else:
        result["text"] = text
    return result


def get_tags(obj, given_tags):
    "Interpret the given tags in terms of actually existing tags."
    existing_tags = get(obj, "tags")
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
        if len(candidates) == 1:
            result.append(candidates[0])
    return result or None


if __name__ == "__main__":
    main()
