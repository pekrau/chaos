"Event pages."

import calendar
import copy
import datetime as dt
import itertools
import math

from fasthtml.common import *
import yaml

import components
import constants
import items
import markdown
import utils

app, rt = components.get_app_rt()


@rt("/")
def get(date: str = None):
    "Form for adding an event."
    return (
        Title("Add event"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add ", components.get_event_icon(), "event"),
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
                            value=date or "",
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
                            value=date or "",
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
                Input(type="submit", value="Add"),
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
    subevents = set(items.get_events_within(event.start, event.end))
    subevents.remove(event)
    subevents = sorted(subevents, key=lambda e: (len(e), e.start), reverse=True)
    superevents = set(items.get_events_overlapping(event.start, event.end))
    superevents.remove(event)
    superevents = set(superevents).difference(subevents)
    superevents = sorted(superevents, key=lambda e: (len(e), e.start), reverse=True)
    return (
        Title(event),
        components.get_clipboard_script(),
        components.get_header_item_view(event),
        Main(
            components.get_text_card(
                event,
                header=Header(
                    Div(
                        Strong(event.display(date=True)),
                        f" ({event.duration()})",
                        cls="center",
                    ),
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
                    title=event.category.capitalize(),
                ),
            ),
            Card(
                get_vertical_display(event.start, event.end, subevents),
                cls="container",
            ),
            components.get_items_display(superevents, title="Overlaps"),
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
                            value=str(event._end).split()[0],  # Note: uses '_end'!
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
                    Li(components.get_nav_menu()),
                    Li(components.get_event_icon(), title),
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
                Fieldset(
                    Legend("Recurring every..."),
                    Input(
                        type="radio",
                        id="recur_never",
                        name="recur",
                        checked=True,
                        value="",
                    ),
                    Label("Never", htmlFor="recur_never"),
                    Input(type="radio", id="recur_day", name="recur", value="day"),
                    Label("Day", htmlFor="recur_day"),
                    Input(type="radio", id="recur_week", name="recur", value="week"),
                    Label("Week", htmlFor="recur_week"),
                    Input(type="radio", id="recur_month", name="recur", value="month"),
                    Label("Month", htmlFor="recur_month"),
                    Input(type="radio", id="recur_year", name="recur", value="year"),
                    Label("Year", htmlFor="recur_year"),
                ),
                Fieldset(
                    Label(
                        "Last day",
                        Input(type="date", name="end_date"),
                    ),
                    Label(
                        "Number of times",
                        Input(type="number", name="number", min=1, step=1),
                    ),
                    cls="grid",
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
def post(
    session,
    source: items.File,
    title: str,
    recur: str = None,
    end: str = None,
    number: int = None,
):
    "Actually copy the event, possibly several recurring times."
    assert isinstance(source, items.Event)
    ic(recur, end, number)
    if recur and (end or number):
        if end:
            end = dt.datetime.combine(
                dt.date.fromisoformat(end), dt.time(), tzinfo=constants.TIMEZONE
            )
        start = copy.copy(source.start)
        starts = []
        match recur:
            case "day":
                while True:
                    start = start + dt.timedelta(days=1)
                    if end and start > end:
                        break
                    if number is not None and (number := number - 1) < 0:
                        break
                    starts.append(start)
            case "week":
                while True:
                    start = start + dt.timedelta(days=7)
                    if end and start > end:
                        break
                    if number is not None and (number := number - 1) < 0:
                        break
                    starts.append(start)
            case "month":
                while True:
                    if start.month == 12:
                        month = 1
                        year = start.year + 1
                    else:
                        month = start.month + 1
                        year = start.year
                    day = source.start.day  # Original day used if possible.
                    while True:  # Watch out for shorter months.
                        try:
                            start = dt.datetime(
                                year,
                                month,
                                day,
                                hour=start.hour,
                                minute=start.minute,
                                tzinfo=start.tzinfo,
                            )
                        except ValueError:
                            day -= 1
                        else:
                            break
                    if end and start > end:
                        break
                    if number is not None and (number := number - 1) < 0:
                        break
                    starts.append(start)
            case "year":
                while True:
                    day = source.start.day  # Original day used if possible.
                    while True:  # Watch out for leap year.
                        try:
                            start = dt.datetime(
                                start.year + 1,
                                start.month,
                                day,
                                hour=start.hour,
                                minute=start.minute,
                                tzinfo=start.tzinfo,
                            )
                        except ValueError:  # No such day for the month.
                            day -= 1
                        else:
                            break
                    if end and start > end:
                        break
                    if number is not None and (number := number - 1) < 0:
                        break
                    starts.append(start)
        for start in starts:
            event = items.Event()
            event.title = title.strip()
            event.start = copy.copy(start)
            event.end = start + (source.end - source.start)
            event.text = f"{source.text}\n\nRecurring copy of [[{source.id}]]."
            event.tags = source.tags
            event.category = source.category
            event.write()
        add_toast(session, f"Created {len(starts)} recurring events.", "success")
        if not starts:
            return components.redirect(source.url)
    else:
        event = items.Event()
        event.title = title.strip()
        event.start = copy.copy(source.start)
        event.end = copy.copy(source.end)
        event.text = source.text
        event.tags = source.tags
        event.category = source.category
        event.write()
    return components.redirect(event.url)


@rt("/{event:Item}/delete")
def get(event: items.Item):
    "Ask for confirmation to delete the event."
    assert isinstance(event, items.Event)
    return (
        *components.get_header_item_delete(event),
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
    events = [e for e in items.get_events_overlapping(start, end)]
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
            Tr(Td(get_month_table(month.year, month.month, events, full=False)))
        )
    title = f"Year {year}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_event_icon(), title),
                ),
                Ul(
                    Li(components.get_search_field()),
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
    events = items.get_events_overlapping(first, last)
    title = f"{start.strftime('%B %Y').capitalize()}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_event_icon(), title),
                ),
                Ul(
                    Li(components.get_search_field()),
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
    prev = start - dt.timedelta(days=4)  # Thursday previous week.
    next = end + dt.timedelta(days=3)  # Thursday next week.
    events = items.get_events_overlapping(start, end)
    weekdays = [start] + [start + dt.timedelta(days=day) for day in range(1, 7)]
    thursday = weekdays[3]
    today_ordinal = dt.datetime.now(constants.TIMEZONE).toordinal()
    title = f"w{week} {year}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_event_icon(), title),
                ),
                Ul(
                    Li(components.get_search_field()),
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
                                        f"{d.strftime('%a')} {d.day} {d.strftime('%b')}".capitalize(),
                                        href=d.strftime("/event/day/%Y-%m-%d"),
                                        cls="secondary strong",
                                    ),
                                    cls=(
                                        "today"
                                        if d.toordinal() == today_ordinal
                                        else ""
                                    ),
                                    style="width: 15%",
                                )
                                for d in weekdays
                            ]
                        ),
                        *get_week_rows(weekdays, events, offset=False, full=True),
                        Tr(Td(Div(cls="vspacer"), colspan=7)),
                        Tr(
                            *[
                                Td(
                                    A(
                                        "Add",
                                        href=f"/event?date={d.year}-{d.month:02}-{d.day:02}",
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
    thisday = utils.get_datetime(year, month, day)
    today = dt.date(year, month, day) == dt.date.today()
    prev = thisday - dt.timedelta(days=1)
    next = thisday + dt.timedelta(days=1)

    # First events that extend over more than thisday, sorted by length.
    # Then thisdays events, sorted by start time.
    events = items.get_events_overlapping(thisday, next)
    beyond_thisday = sorted(
        [e for e in events if not e.within(thisday, next)],
        key=lambda e: len(e),
        reverse=True,
    )
    just_thisday = sorted(
        [e for e in events if e.within(thisday, next)], key=lambda e: e.start
    )
    events = beyond_thisday + just_thisday

    title = f"{thisday.strftime('%A').capitalize()} {thisday.day} {thisday.strftime('%B')} {thisday.year}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(
                        components.get_event_icon(), title, cls="today" if today else ""
                    ),
                ),
                Ul(
                    Li(components.get_search_field()),
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
                            thisday.strftime("%A").capitalize(),
                            " ",
                            thisday.day,
                            cls="rmargin",
                        ),
                        A(
                            thisday.strftime("%B"),
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
                            f"w{thisday.strftime('%V').lstrip('0')}",
                            href=f"/event/week/{thisday.year}-{thisday.isocalendar().week}",
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
                get_vertical_display(thisday, next, events),
                Footer(
                    A(
                        "Add",
                        href=f"/event?date={year}-{month:02}-{day:02}",
                        role="button",
                    ),
                ),
            ),
            cls="container",
        ),
    )


def get_month_table(year, month, events, full=True):
    "Generate the display the given events of a specified month."
    today_ordinal = dt.datetime.now(constants.TIMEZONE).toordinal()
    monthdays = list(calendar.Calendar().monthdatescalendar(year, month))
    rows = [
        Tr(
            Td(),
            *[
                Td(d.strftime("%a").capitalize(), style="width: 15%")
                for d in monthdays[0]
            ],
        )
    ]
    for weekdays in monthdays:
        rows.append(
            Tr(
                Th(
                    A(
                        f"w{weekdays[0].strftime('%V').lstrip('0')}",
                        href=f"/event/week/{weekdays[3].year}-{weekdays[3].isocalendar().week}",
                        role="button",
                        cls="outline thin",
                    ),
                    cls="minwidth",
                ),
                *[
                    Th(
                        A(
                            d.day,
                            href=f"/event/day/{d.year}-{d.month:02}-{d.day:02}",
                            cls=(
                                "secondary strong"
                                if d.month == month
                                else "secondary small"
                            ),
                        ),
                        cls="today" if d.toordinal() == today_ordinal else "",
                    )
                    for d in weekdays
                ],
            )
        )
        first = utils.to_datetime(weekdays[0])
        last = utils.to_datetime(weekdays[6]) + dt.timedelta(days=1)
        rows.extend(
            get_week_rows(
                weekdays, [e for e in events if e.overlap(first, last)], full=full
            )
        )
        rows.append(Tr(Td(Div(cls="vspacer"), colspan=8)))
    return Table(*rows, cls="days")


def get_week_rows(weekdays, events, offset=True, full=True):
    "Return rows for the events of the week."
    weekdays = [utils.to_datetime(d) for d in weekdays]
    start = weekdays[0]
    end = weekdays[6] + dt.timedelta(days=1)
    row_cells = []
    events = list(events)  # Make copy to avoid changing incoming argument.
    while events:
        cells = []
        events_list = get_next_events_list(events, start, end)
        events = set(events).difference(events_list)
        sum_colspan = 0
        for event in events_list:
            if event.start < start:
                if event._end > end:
                    colspan = 7
                else:
                    colspan = event.end_weekday_number
                    sum_colspan += colspan
            elif event._end > end:
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
            if full:
                cells.append(
                    Td(
                        Div(
                            A(
                                event.display(year=start.year),
                                href=event.url,
                                cls="black",
                            ),
                            title=f"{event.category.capitalize()}: {event.title}",
                            cls=get_event_classes(event, start, end),
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
                            cls="black",
                        ),
                        title=f"{event.category.capitalize()}: {event.title}",
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


def get_vertical_display(start, end, subevents):
    "Return a vertical display of the events."
    if not subevents:
        return I("No subevents.", cls="lmargin")
    subevents = list(subevents)  # Make copy to avoid changing incoming argument.
    if (end - start).total_seconds() <= 24 * 3600:  # One day or less.
        day = dt.date(start.year, start.month, start.day)
        hours = [
            dt.datetime.combine(day, dt.time(hour=h, tzinfo=start.tzinfo))
            for h in range(24)
        ]
        rows = [
            [
                Td(
                    hour.strftime("%H:%M"),
                )
            ]
            for hour in hours
        ]
        while subevents:
            events_list = get_next_events_list(subevents, start, end, hours=True)
            subevents = set(subevents).difference(events_list)
            for subevent in events_list:
                for slot, hour in enumerate(hours):
                    if hour.hour == subevent.start.hour:
                        rows[slot].append(
                            Td(
                                Div(
                                    A(
                                        f"{subevent.display(year=start.year)}: {subevent.title}",
                                        href=subevent.url,
                                        cls="black",
                                    ),
                                    Br(),
                                    NotStr(markdown.to_html(subevent.text)),
                                    cls=get_event_classes(
                                        subevent, start, end, vertical=True
                                    ),
                                    title=subevent.category.capitalize(),
                                ),
                                rowspan=max(
                                    1,
                                    math.floor(
                                        (subevent.end - hour).total_seconds() / 3600
                                    ),
                                ),
                            )
                        )
    else:
        days = [
            dt.datetime.fromordinal(d)
            for d in range(start.toordinal(), end.toordinal())
        ]
        rows = [
            [
                Td(
                    A(
                        day.strftime("%Y-%m-%d"),
                        href=f"/event/day/{day.strftime('%Y-%m-%d')}",
                        cls="nobr",
                    )
                )
            ]
            for day in days
        ]
        while subevents:
            events_list = get_next_events_list(subevents, start, end)
            subevents = set(subevents).difference(events_list)
            for subevent in events_list:
                for slot, day in enumerate(days):
                    if day.toordinal() == subevent.start.toordinal():
                        rows[slot].append(
                            Td(
                                Div(
                                    A(
                                        f"{subevent.display(year=start.year)}: {subevent.title}",
                                        href=subevent.url,
                                        cls="black",
                                    ),
                                    cls=get_event_classes(subevent, start, end),
                                    title=subevent.category.capitalize(),
                                ),
                                rowspan=subevent.days,
                            )
                        )
    return Table(*[Tr(*row) for row in rows], cls="vertical")


def get_next_events_list(events, start, end, hours=False):
    "Return the next sorted list of non-overlapping events."
    if hours:
        non_overlapping = get_non_overlapping_hours(events)
    else:
        non_overlapping = get_non_overlapping_days(events)
    non_overlapping.sort(
        key=lambda s: (
            sum([e.overlap(start, end) for e in s]),
            sum([len(e) for e in s]),
        ),
        reverse=True,
    )
    return sorted(non_overlapping[0])


def get_non_overlapping_hours(events, candidates=None):
    "Return a list of of mutually hour-wise non-overlapping event lists."
    events = list(events)
    result = []
    for pos, e in enumerate(events):
        if candidates is None:
            result.append([e])
            result.extend(get_non_overlapping_hours(events[pos + 1 :], [e]))
        elif not any([e.overlap_hours(c.start, c.end) for c in candidates]):
            new_candidates = candidates + [e]
            result.append(new_candidates)
            result.extend(get_non_overlapping_hours(events[pos + 1 :], new_candidates))
    return result


def get_non_overlapping_days(events, candidates=None):
    "Return a list of of mutually day-wise non-overlapping event lists."
    events = list(events)
    result = []
    for pos, e in enumerate(events):
        if candidates is None:
            result.append([e])
            result.extend(get_non_overlapping_days(events[pos + 1 :], [e]))
        elif not any([e.overlap_days(c.start, c.end) for c in candidates]):
            new_candidates = candidates + [e]
            result.append(new_candidates)
            result.extend(get_non_overlapping_days(events[pos + 1 :], new_candidates))
    return result


def get_event_classes(event, start, end, vertical=False):
    "Get the event classes; border and category."
    if event.start < start:
        if event.end > end:
            if vertical:
                border = f"border-open-top-bottom"
            else:
                border = f"border-open-left-right"
        elif vertical:
            border = f"border-open-top"
        else:
            border = f"border-open-left"
    elif event.end > end:
        if vertical:
            border = f"border-open-bottom"
        else:
            border = f"border-open-right"
    else:
        border = f"border-closed"
    return f"border {border} {event.category}"
