"Output components."

from fasthtml.common import *

import constants


def chaos_icon():
    return A(
        Img(
            src="/Greek_lc_chi_icon64.png",
            height=24,
            width=24,
            cls="white"),
        title="chaos",
        role="button",
        cls="secondary outline",
        href="/")


def entry_icon(entry):
    match entry.type:
        case constants.NOTE:
            filename = "card-text.svg"
        case constants.LINK:
            filename = "link-45deg.svg"
        case constants.FILE:
            filename = "file-binary.svg"
        case _:
            raise NotImplementedError
    return Img(src=f"/{filename}")

def search_form():
    return Form(
        Input(
            name="term",
            type="search",
            placeholder="Search...",
            aria_label="Search",
            autofocus=True,
        ),
        style="margin-bottom: 2px; padding-top: 0;",
        role="search",
        action="/search",
    )

def get_entry_clipboard(entry):
    return Img(
        src="/clipboard.svg",
        title="Copy entry link to clipboard",
        style="cursor: pointer;",
        cls="to_clipboard white",
        data_clipboard_action="copy",
        data_clipboard_text=f"[{entry.title}](/entry/{entry})",
    )
