"Event pages."

import calendar
import copy
import datetime as dt
import itertools

from fasthtml.common import *
import yaml

import components
import constants
import items
import utils

app, rt = components.get_app_rt()


@rt("/")
def get(start_date: str = None):
    "Form for adding an event."
    title = "Add event"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(),
                Fieldset(
                    Label(
                        "Start date",
                        Input(
                            type="date",
                            name="start_date",
                            value=start_date or "",
                            required=True,
                        ),
                    ),
                    Label(
                        "Start time",
                        Input(
                            type="time",
                            name="start_time",
                        ),
                    ),
                    Label(
                        "End date",
                        Input(
                            type="date",
                            name="end_date",
                        ),
                    ),
                    Label(
                        "End time",
                        Input(
                            type="time",
                            name="end_time",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add event"),
                action="/event/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(
    title: str,
    start_date: str,
    text: str,
    tags: list[str] = None,
    start_time: str = None,
    end_date: str = None,
    end_time: str = None,
):
    "Actually add an event."
    event = items.Event()
    event.title = title.strip() or "no title"
    event.text = text.strip()
    event.set_start(start_date, start_time)
    event.set_end(end_date, end_time)
    event.check()
    event.tags = tags
    event.write()
    return components.redirect(event.url)


@rt("/{event:Item}")
def get(event: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the event."
    assert isinstance(event, items.Event)
    return (
        Title(event),
        components.get_clipboard_script(),
        components.get_header_item_view(event),
        Main(
            components.get_text_card(
                event,
                header=Header(
                    Div(
                        Strong(event.nice(date=True, year=True)),
                        f" ({event.duration})",
                        cls="center bmargin1",
                    ),
                    Div(
                        Div("prev"),
                        Div(
                            A(
                                f"{event.start.strftime('%a').capitalize()} {event.start.strftime('%d').lstrip('0')}",
                                href=f"/event/day/{event.start.year}-{event.start.month:02}-{event.start.day:02}",
                                role="button",
                                cls="outline thin rmargin",
                            ),
                            A(
                                event.start.strftime("%b"),
                                href=f"/event/month/{event.start.year}-{event.start.month:02}",
                                role="button",
                                cls="outline thin rmargin",
                            ),
                            A(
                                event.start.year,
                                href=f"/event/year/{event.start.year}",
                                role="button",
                                cls="outline thin rmargin",
                            ),
                            A(
                                f"v{event.start.strftime('%V').lstrip('0')}",
                                href=f"/event/week/{event.start.year}-{event.start.isocalendar().week}",
                                role="button",
                                cls="outline thin right",
                            ),
                            cls="center",
                        ),
                        Div("next", cls="right"),
                        cls="grid",
                    ),
                ),
            ),
            Form(
                components.get_refs_card(event, refs_page),
                components.get_tags_card(event, tags_page),
                action=event.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(event),
        components.get_clipboard_activate(),
    )


@rt("/{event:Item}/edit")
def get(event: items.Item):
    "Form for editing an event."
    assert isinstance(event, items.Event)
    return (
        *components.get_header_item_edit(event),
        Main(
            Form(
                components.get_title_input(event.title),
                Fieldset(
                    Label(
                        "Start date",
                        Input(
                            type="date",
                            name="start_date",
                            value=str(event.start).split()[0],
                            required=True,
                        ),
                    ),
                    Label(
                        "Start time",
                        Input(
                            type="time",
                            name="start_time",
                            value=":".join(str(event.start).split()[1].split(":")[0:2]),
                        ),
                    ),
                    Label(
                        "End date",
                        Input(
                            type="date",
                            name="end_date",
                            value=str(event.end).split()[0],
                        ),
                    ),
                    Label(
                        "End time",
                        Input(
                            type="time",
                            name="end_time",
                            value=":".join(str(event.end).split()[1].split(":")[0:2]),
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(event.text),
                components.get_tags_input(event.tags),
                Input(type="submit", value="Save"),
                action=f"{event.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(event.url),
            cls="container",
        ),
    )


@rt("/{event:Item}/edit")
def post(
    event: items.Item,
    title: str,
    text: str,
    start_date: str,
    start_time: str = None,
    end_date: str = None,
    end_time: str = None,
    tags: list[str] = None,
):
    "Actually edit the event."
    assert isinstance(event, items.Event)
    event.title = title.strip()
    event.text = text.strip()
    event.set_start(start_date, start_time)
    event.set_end(end_date, end_time)
    event.check()
    event.tags = tags
    event.write()
    return components.redirect(event.url)


@rt("/{event:Item}/copy")
def get(event: items.Item):
    "Form for making a copy of the event."
    assert isinstance(event, items.Event)
    title = f"Copy '{event}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(event)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=event.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy event"),
                action=f"{event.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(event.url),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the event."
    assert isinstance(source, items.Event)
    event = items.Event()
    event.title = title.strip()
    event.start = copy.copy(source.start)
    event.end = copy.copy(source.end)
    event.text = source.text
    event.write()
    return components.redirect(event.url)


@rt("/{event:Item}/delete")
def get(event: items.Item):
    "Ask for confirmation to delete the event."
    assert isinstance(event, items.Event)
    title = f"Delete '{event}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(event)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the event? All data will be lost."),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{event.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(event.url),
            cls="container",
        ),
    )


@rt("/{event:Item}/delete")
def post(event: items.Item):
    "Actually delete the event."
    assert isinstance(event, items.Event)
    event.delete()
    return components.redirect()


@rt("/year/")
def get():
    "Redirect to the current year."
    return components.redirect(f"/event/year/{dt.date.today().year}")


@rt("/year/{year}")
def get(year: int):
    "Display events during a specified year."
    start = dt.datetime(year, 1, 1, tzinfo=constants.TIMEZONE)
    end = dt.datetime(year + 1, 1, 1, tzinfo=constants.TIMEZONE)
    events = sorted([p for p in items.get_items(type="event") if p.within(start, end)])
    months = [dt.datetime(year, m, 1, tzinfo=constants.TIMEZONE)
              for m in range(1, 13)]
    rows = []
    for quarter in itertools.batched(months, 3):
        rows.append(Tr(*[Td(Strong(A(m.strftime("%b").capitalize(),
                              href=f"/event/month/{year}-{m.month}",
                              cls="secondary"
                                     )),
                            )
                         for m in quarter]))
    title = f"Year {year}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(icon=components.get_event_icon())),
                    Li(title),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    Div(
                        A(
                            year - 1,
                            href=f"/event/year/{year-1}",
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Strong(year, cls="center"),
                    Div(
                        A(
                            year + 1,
                            href=f"/event/year/{year+1}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                Table(*rows, cls="overflow-auto center"),
            ),
            cls="container",
        ),
    )


@rt("/month/")
def get():
    "Redirect to the current month."
    today = dt.date.today()
    return components.redirect(f"/event/month/{today.year}-{today.month}")


@rt("/month/{year}-{month}")
def get(year: int, month: int):
    "Display events during a specified month."
    start = dt.datetime(year, month, 1, tzinfo=constants.TIMEZONE)
    if month == 1:
        prev = dt.datetime(year - 1, 12, 1, tzinfo=constants.TIMEZONE)
        next = dt.datetime(year, 2, 1, tzinfo=constants.TIMEZONE)
    elif month == 12:
        prev = dt.datetime(year, 11, 1, tzinfo=constants.TIMEZONE)
        next = dt.datetime(year + 1, 1, 1, tzinfo=constants.TIMEZONE)
    else:
        prev = dt.datetime(year, month - 1, 1, tzinfo=constants.TIMEZONE)
        next = dt.datetime(year, month + 1, 1, tzinfo=constants.TIMEZONE)
    events = sorted(
        [p for p in items.get_items(type="event") if p.overlap(start, next)]
    )
    month_days = list(calendar.Calendar().itermonthdates(year, month))
    rows = [
        Tr(
            Td(),
            *[Td(d.strftime("%a").capitalize()) for d in month_days[0:7]])
    ]
    for week in itertools.batched(month_days, 7):
        rows.append(
            Tr(
                Td(
                    A(
                        f"v{week[0].strftime('%V').lstrip('0')}",
                        href=f"/event/week/{week[0].year}-{week[0].isocalendar().week}",
                        role="button",
                        cls="outline thin",
                    ),
                    cls="minimize",
                ),
                *[
                    Td(
                        A(
                            utils.date(d, weekday=False, year=year),
                            href=f"/event/day/{d.year}-{d.month:02}-{d.day:02}",
                            cls="secondary strong",
                        ),
                    )
                    for d in week
                ]
            )
        )
        days = []
        for day in week:
            day1 = dt.datetime(day.year, day.month, day.day, tzinfo=constants.TIMEZONE)
            day2 = day1 + dt.timedelta(days=1)
            day_events = [e for e in events if e.overlap(day1, day2)]
            if day_events:
                days.append(
                    Td(
                        *[
                            A(
                                Div(
                                    e.nice(end=False, title=True),
                                    cls="bmargin3 border border-closed",
                                ),
                                href=e.url,
                                cls="plain",
                            )
                            for e in day_events
                        ],
                        cls="top",
                    )
                )
            else:
                days.append(Td(Div(cls="bmargin3")))
        rows.append(Tr(Td(), *days))
    title = f"{start.strftime('%B %Y').capitalize()}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(icon=components.get_event_icon())),
                    Li(title),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    Div(
                        A(
                            prev.strftime("%B %Y").capitalize(),
                            href=f"/event/month/{prev.strftime('%Y-%m')}",
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Strong(
                        Span(start.strftime("%B").capitalize(), cls="rmargin"),
                        A(
                            start.strftime("%Y"),
                            href=f"/event/year/{year}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="center",
                    ),
                    Div(
                        A(
                            next.strftime("%B %Y").capitalize(),
                            href=f"/event/month/{next.strftime('%Y-%m')}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                Table(*rows, cls="overflow-auto center"),
            ),
            cls="container",
        ),
    )


@rt("/week/")
def get():
    "Redirect to the current week."
    today = dt.date.today().isocalendar()
    return components.redirect(f"/event/week/{today.year}-{today.week}")


@rt("/week/{year}-{week}")
def get(year: int, week: int):
    "Display events during a specified week."
    start = dt.datetime.strptime(f"{year}-{week}-1", "%G-%V-%u").replace(
        tzinfo=constants.TIMEZONE
    )
    try:
        end = dt.datetime.strptime(f"{year}-{week+1}-1", "%G-%V-%u").replace(
            tzinfo=constants.TIMEZONE
        )
    except ValueError:
        end = dt.datetime.strptime(f"{year+1}-{1}-1", "%G-%V-%u").replace(
            tzinfo=constants.TIMEZONE
        )
    last = end - dt.timedelta(days=1)
    try:
        prev = dt.datetime.strptime(f"{year}-{week-1}-1", "%G-%V-%u").replace(
            tzinfo=constants.TIMEZONE
        )
    except ValueError:
        for prev_week in [53, 52, 51]:
            try:
                prev = dt.datetime.strptime(
                    f"{year-1}-{prev_week}-1", "%G-%V-%u"
                ).replace(tzinfo=constants.TIMEZONE)
            except ValueError:
                continue
            else:
                break
    try:
        next = dt.datetime.strptime(f"{year}-{week+1}-1", "%G-%V-%u").replace(
            tzinfo=constants.TIMEZONE
        )
    except ValueError:
        next = dt.datetime.strptime(f"{year+1}-1-1", "%G-%V-%u").replace(
            tzinfo=constants.TIMEZONE
        )
    events = sorted(
        [p for p in items.get_items(type="event") if p.overlap(start, next)]
    )
    weekdays = utils.get_week(start)
    title = f"v{week} {year}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(icon=components.get_event_icon())),
                    Li(title),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    Div(
                        A(
                            utils.week(prev, year=True),
                            href=f"/event/week/{prev.strftime('%Y-%V')}",
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Div(
                        Strong(f"v{week}", cls="rmargin"),
                        A(
                            weekdays[3].strftime("%b"),
                            href=weekdays[3].strftime("/event/month/%Y-%m"),
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            weekdays[3].strftime("%Y"),
                            href=weekdays[3].strftime("/event/year/%Y"),
                            role="button",
                            cls="outline thin",
                        ),
                        cls="center",
                    ),
                    Div(
                        A(
                            utils.week(next, year=True),
                            href=f"/event/week/{next.strftime('%Y-%V')}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                Table(
                    Tr(
                        *[
                            Td(
                                A(
                                    utils.date(d, year=year),
                                    href=f"/event/day/{utils.date_iso(d)}",
                                    cls="secondary strong",
                                ),
                            )
                            for d in weekdays
                        ]
                    ),
                    Tr(
                        *[
                            Td(
                                Div(
                                    *[
                                        A(
                                            Div(
                                                f"{e.nice(end=False, title=True)}",
                                                cls="border border-closed",
                                            ),
                                            href=e.url,
                                            cls="plain",
                                        )
                                        for e in events
                                        if e.within(d, d + dt.timedelta(days=1))
                                    ],
                                    cls="bmargin3",
                                ),
                                cls="top",
                            )
                            for d in weekdays
                        ]
                    ),
                    Tr(
                        *[
                            Td(
                                A(
                                    "Add event...",
                                    href=f"/event?start_date={d.year}-{d.month:02}-{d.day:02}",
                                    role="button",
                                    cls="thin",
                                ),
                            )
                            for d in weekdays
                        ]
                    ),
                    cls="overflow-auto center",
                ),
            ),
            cls="container",
        ),
    )


@rt("/day/")
def get():
    "Redirect to the current day."
    return components.redirect(f"/event/day/{dt.date.today().isoformat()}")


@rt("/day/{year}-{month}-{day}")
def get(year: int, month: int, day: int):
    "Display events during a specified day."
    start = dt.datetime(year, month, day, tzinfo=constants.TIMEZONE)
    end = start + dt.timedelta(days=1)
    prev = start - dt.timedelta(days=1)
    events = sorted([p for p in items.get_items(type="event") if p.overlap(start, end)])
    title = utils.date(start, year=True).capitalize()
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(icon=components.get_event_icon())),
                    Li(title),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    Div(
                        A(
                            utils.date(prev),
                            href=f"/event/day/{utils.date_iso(prev)}",
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Div(
                        Strong(
                            start.strftime("%a").capitalize(),
                            " ",
                            start.strftime("%d").lstrip("0"),
                            cls="rmargin",
                        ),
                        A(
                            start.strftime("%b"),
                            href=f"/event/month/{year}-{month}",
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            year,
                            href=f"/event/year/{year}",
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            f"v{start.strftime('%V').lstrip('0')}",
                            href=f"/event/week/{start.year}-{start.isocalendar().week}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="center",
                    ),
                    Div(
                        A(
                            utils.date(end),
                            href=f"/event/day/{utils.date_iso(end)}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                *[
                    Div(
                        A(
                            e.nice(date=not e.within(start, end), title=True),
                            href=e.url,
                        ),
                        Br(),
                        NotStr(e.html or ""),
                        cls="border border-closed",
                    )
                    for e in events
                ],
                Footer(
                    A(
                        "Add event...",
                        href=f"/event?start_date={year}-{month:02}-{day:02}",
                        role="button",
                    ),
                ),
            ),
            cls="container",
        ),
    )
