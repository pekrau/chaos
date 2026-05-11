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
                    Label(
                        "Category",
                        Select(
                            Option("", disable=True, selected=True),
                            *[Option(c, cls=c) for c in constants.EVENT_CATEGORIES],
                            name="category",
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
    category: str = None,
):
    "Actually add an event."
    event = items.Event()
    event.title = title.strip() or "no title"
    event.text = text.strip()
    event.set_start(start_date, start_time)
    event.set_end(end_date, end_time)
    event.check()
    event.tags = tags
    event.category = category
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
                    Div(event.category.capitalize()),
                    Div(Strong(event.period(date=True)), f" ({event.duration()})"),
                    Div(
                        A(
                            f"{event.weekday_short.capitalize()} {event.start.day}",
                            href=f"/event/day/{event.isodate()}",
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            event.month,
                            href=f"/event/month/{event.isodate(day=False)}",
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            event.start.year,
                            href=f"/event/year/{event.isodate(month=False, day=False)}",
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            f"w{event.week}",
                            href=f"/event/week/{event.isodate(week=True)}",
                            role="button",
                            cls="outline thin right",
                        ),
                        cls="right",
                    ),
                    cls=f"grid {event.category}",
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
                    Label(
                        "Category",
                        Select(
                            *[
                                Option(c, cls=c, selected=c == event.category)
                                for c in constants.EVENT_CATEGORIES
                            ],
                            name="category",
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
    category: str = None,
):
    "Actually edit the event."
    assert isinstance(event, items.Event)
    event.title = title.strip()
    event.text = text.strip()
    event.set_start(start_date, start_time)
    event.set_end(end_date, end_time)
    event.check()
    event.tags = tags
    event.category = category
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
    events = [
        e
        for e in items.get_items(type="event")
        if e.overlap(start, end) and len(e) > 24 * 60
    ]
    rows = []
    for month in [utils.get_datetime(year, m) for m in range(1, 13)]:
        rows.append(
            Tr(
                Td(
                    Strong(
                        A(
                            month.strftime("%B").capitalize(),
                            href=f"/event/month/{month.year}-{month.month}",
                            cls="secondary",
                        )
                    )
                )
            )
        )
        rows.append(
            Tr(Td(get_month_table(month.year, month.month, events, thick=False)))
        )
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
                Div(
                    Table(*rows, cls="days"),
                    cls="overflow-auto",
                ),
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
    days = list(calendar.Calendar().monthdatescalendar(year, month))
    first = utils.to_datetime(days[0][0])
    last = utils.to_datetime(days[-1][-1]) + dt.timedelta(days=1)
    start = utils.get_datetime(year, month)
    prev = first - dt.timedelta(days=1)

    # Fetch events overlapping any of the weeks at the ends of the month display.
    events = [p for p in items.get_items(type="event") if p.overlap(first, last)]

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
                            last.strftime("%B %Y").capitalize(),
                            href=f"/event/month/{last.strftime('%Y-%m')}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                Div(
                    get_month_table(year, month, events),
                    cls="overflow-auto",
                ),
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
    events = [p for p in items.get_items(type="event") if p.overlap(start, next)]
    weekdays = [start] + [start + dt.timedelta(days=day) for day in range(1, 7)]
    thursday = weekdays[3]
    title = f"w{week} {year}"
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
                            f"w{prev.strftime('%V').lstrip('0')}",
                            f" {prev.year}" if prev.year != thursday.year else "",
                            href=f"/event/week/{prev.strftime('%Y-%V')}",
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Div(
                        Strong(f"w{week}", cls="rmargin"),
                        A(
                            thursday.strftime("%B"),
                            href=thursday.strftime("/event/month/%Y-%m"),
                            role="button",
                            cls="outline thin rmargin",
                        ),
                        A(
                            thursday.strftime("%Y"),
                            href=thursday.strftime("/event/year/%Y"),
                            role="button",
                            cls="outline thin",
                        ),
                        cls="center",
                    ),
                    Div(
                        A(
                            f"w{next.strftime('%V').lstrip('0')}",
                            f" {next.year}" if next.year != thursday.year else "",
                            href=f"/event/week/{next.strftime('%Y-%V')}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls="grid",
                ),
                Div(
                    Table(
                        Tr(
                            *[
                                Td(
                                    A(
                                        utils.date(d, month=True, year=year),
                                        href=d.strftime("/event/day/%Y-%m-%d"),
                                        cls="secondary strong",
                                    ),
                                    style="width: 15%",
                                )
                                for d in weekdays
                            ]
                        ),
                        *get_week_rows(weekdays, events, offset=False, thick=True),
                        Tr(Td(Div(cls="vspacer"), colspan=7)),
                        Tr(
                            *[
                                Td(
                                    A(
                                        "Add",
                                        href=f"/event?start_date={d.year}-{d.month:02}-{d.day:02}",
                                        role="button",
                                        cls="thin",
                                    ),
                                )
                                for d in weekdays
                            ]
                        ),
                        cls="days",
                    ),
                    cls="overflow-auto",
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
    today = utils.get_datetime(year, month, day)
    prev = today - dt.timedelta(days=1)
    next = today + dt.timedelta(days=1)

    # First events that extend over more than today, sorted by length.
    # Then todays events, sorted by start time.
    events = [e for e in items.get_items(type="event") if e.overlap(today, next)]
    beyond_today = sorted(
        [e for e in events if not e.within(today, next)],
        key=lambda e: len(e),
        reverse=True,
    )
    just_today = sorted(
        [e for e in events if e.within(today, next)], key=lambda e: e.start
    )
    events = beyond_today + just_today

    title = f"{today.strftime('%A').capitalize()} {today.day} {today.strftime('%B')} {today.year}"
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
                            f"{prev.day} {prev.strftime('%b')}",
                            href=prev.strftime("/event/day/%Y-%m-%d"),
                            role="button",
                            cls="outline thin",
                        ),
                    ),
                    Div(
                        Strong(
                            today.strftime("%A").capitalize(),
                            " ",
                            today.day,
                            cls="rmargin",
                        ),
                        A(
                            today.strftime("%B"),
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
                            f"w{today.strftime('%V').lstrip('0')}",
                            href=f"/event/week/{today.year}-{today.isocalendar().week}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="center",
                    ),
                    Div(
                        A(
                            f"{next.day} {next.strftime('%b')}",
                            href=next.strftime("/event/day/%Y-%m-%d"),
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
                            f"{e.period()} {e.title}",
                            href=e.url,
                            cls="black",
                        ),
                        Br(),
                        NotStr(e.html or ""),
                        cls=get_event_classes(e, today, next) + " border-plus",
                    )
                    for e in events
                ],
                Footer(
                    A(
                        "Add",
                        href=f"/event?start_date={year}-{month:02}-{day:02}",
                        role="button",
                    ),
                ),
            ),
            cls="container",
        ),
    )


def get_month_table(year, month, events, thick=True):
    "Generate the display the given events of a specified month."
    monthdays = list(calendar.Calendar().monthdatescalendar(year, month))
    rows = [Tr(Td(), *[Td(d.strftime("%a").capitalize(), style="width: 15%") for d in monthdays[0]])]
    for weekdays in monthdays:
        rows.append(
            Tr(
                Th(
                    A(
                        f"w{weekdays[0].strftime('%V').lstrip('0')}",
                        href=f"/event/week/{weekdays[0].year}-{weekdays[0].isocalendar().week}",
                        role="button",
                        cls="outline thin",
                    ),
                    cls="minwidth",
                ),
                *[
                    Th(
                        A(
                            utils.date(d, weekday=False, month=month, year=year),
                            href=f"/event/day/{d.year}-{d.month:02}-{d.day:02}",
                            cls="secondary strong",
                        ),
                    )
                    for d in weekdays
                ],
            )
        )
        first = utils.to_datetime(weekdays[0])
        last = utils.to_datetime(weekdays[6]) + dt.timedelta(days=1)
        rows.extend(
            get_week_rows(
                weekdays, [e for e in events if e.overlap(first, last)], thick=thick
            )
        )
        rows.append(Tr(Td(Div(cls="vspacer"), colspan=8)))
    return Table(*rows, cls="days")


def get_week_rows(weekdays, events, offset=True, thick=False):
    """Return rows for the events of the week.
    NOTE: 'events' is depleted during execution.
    """
    weekdays = [utils.to_datetime(d) for d in weekdays]
    start = weekdays[0]
    end = weekdays[6] + dt.timedelta(days=1)
    row_cells = []
    while events:
        cells = []
        events_set = get_next_events(events, start, end)
        events = set(events).difference(events_set)
        sum_colspan = 0
        for event in events_set:
            if event.start < start:
                if event.end > end:
                    colspan = 7
                else:
                    colspan = event.end_weekday_number + 1
                    sum_colspan += colspan
            elif event.end > end:
                first = event.weekday_number
                if pad := first - sum_colspan - 1:
                    cells.append(Td(colspan=pad))
                colspan = 8 - first
            else:
                first = event.weekday_number
                last = event.end_weekday_number
                if pad := first - sum_colspan - 1:
                    cells.append(Td(colspan=pad))
                colspan = last - first + 1
                sum_colspan += pad + colspan
            if thick:
                cells.append(
                    Td(
                        A(
                            Div(
                                f"{event.period()} {event.title}",
                                cls=get_event_classes(event, start, end),
                            ),
                            href=event.url,
                            title=event.category.capitalize(),
                            cls="black",
                        ),
                        colspan=colspan,
                    )
                )
            else:
                cells.append(
                    Td(
                        A(
                            Div(cls="vspacer " + get_event_classes(event, start, end)),
                            href=event.url,
                            title=f"{event.category.capitalize()}: {event.period()} {event.title}",
                            cls="black",
                        ),
                        colspan=colspan,
                    )
                )
        row_cells.append(cells)
    if offset:
        if row_cells:
            result = [Tr(Td(rowspan=max(1, len(row_cells))), *row_cells[0])]
            result.extend([Tr(*c) for c in row_cells[1:]])
        else:
            result = [Tr(Td())]
    else:
        result = [Tr(*c) for c in row_cells]
    return result


def get_next_events(events, start, end, candidates=None):
    "Return the next set of non-overlapping events."
    non_overlapping = get_non_overlapping(events)
    non_overlapping.sort(
        key=lambda s: (
            sum([e.overlap(start, end) for e in s]),
            sum([len(e) for e in s]),
        ),
        reverse=True,
    )
    return sorted(non_overlapping[0])


def get_non_overlapping(events, candidates=None):
    "Return a list of of mutually non-overlapping event lists."
    events = list(events)
    result = []
    for pos, e in enumerate(events):
        if candidates is None:
            result.append([e])
            result.extend(get_non_overlapping(events[pos + 1 :], [e]))
        elif not any([e.overlap(c.start, c.end) for c in candidates]):
            new_candidates = candidates + [e]
            result.append(new_candidates)
            result.extend(get_non_overlapping(events[pos + 1 :], new_candidates))
    return result


def get_event_classes(event, start, end):
    "Get the event classes; border and category."
    if event.start < start:
        if event.end > end:
            border = f"border-open-both"
        else:
            border = f"border-open-left"
    elif event.end > end:
        border = f"border-open-right"
    else:
        border = f"border-closed"
    return f"border {border} {event.category}"
