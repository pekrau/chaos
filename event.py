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
    soon = dt.datetime.now() + dt.timedelta(hours=1)
    date = date or soon.date().isoformat()
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
                components.get_title_input(autofocus=True),
                get_period_edit(date),
                Label(
                    "Category",
                    Select(
                        *[Option(c, cls=c) for c in constants.EVENT_CATEGORIES],
                        name="category",
                    ),
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
    start_time: str = None,
    end_date: str = None,
    end_time: str = None,
    weeks: int = None,
    days: int = None,
    hours: int = None,
    minutes: int = None,
    tags: list[str] = None,
    category: str = None,
):
    "Actually add an event."
    event = items.Event()
    event.title = title
    event.text = text.strip()
    # Start date is always given.
    start = dt.datetime.fromisoformat(start_date)
    # Add start time, if given.
    if start_time:
        start = dt.datetime.combine(start.date(), dt.time.fromisoformat(start_time))
    # Duration, if given.
    duration = items.Duration(weeks=weeks, days=days, hours=hours, minutes=minutes)
    # End datetime, if given.
    if end_date:
        end = dt.datetime.fromisoformat(end_date)
        # End time given.
        if end_time:
            end = dt.datetime.combine(end.date(), dt.time.fromisoformat(end_time))
    # Only end time given; use start date to set the end date.
    elif end_time:
        end = dt.datetime.combine(start, dt.time.fromisoformat(end_time))
    # No end time, but start time given; either explicit duration or 1 hour.
    elif start_time:
        if duration:
            end = start + duration.timedelta
        else:
            end = start + dt.timedelta(hours=1)
    # No end time and no start time; either explicit duration or 1 day.
    elif duration:
        end = start + duration.timedelta
    else:
        end = start + dt.timedelta(days=1)
    event.set(start, end)
    event.tags = tags
    event.category = category
    event.write()
    return components.redirect(event.url)


@rt("/{event:Item}")
def get(event: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the event."
    assert isinstance(event, items.Event)
    subevents = set(
        [e for e in items.get_items("event") if e.within(event.start, event.end)]
    )
    subevents.remove(event)
    subevents = sorted(subevents, key=lambda e: (len(e), e.start), reverse=True)
    superevents = set(
        [e for e in items.get_items("event") if e.overlap_days(event.start, event.end)]
    )
    superevents.remove(event)
    superevents = set(superevents).difference(subevents)
    superevents = sorted(superevents, key=lambda e: (len(e), e.start), reverse=True)
    return (
        Title(event),
        components.get_clipboard_script(),
        components.get_header_item_view(
            event, operations=[A("Create recurring...", href=f"{event.url}/recurring")]
        ),
        Main(
            components.get_text_card(
                event,
                header=Header(
                    Div(
                        Strong(event.display(date=True)),
                        f" ({event.duration})",
                        cls="center",
                    ),
                    Div(
                        A(
                            f"{event.weekday_short.capitalize()} {event.start.day}",
                            href=f"/event/day/{event.isodate()}",
                            role="button",
                            cls="outline thin",
                        ),
                        A(
                            event.month,
                            href=f"/event/month/{event.isodate(day=False)}",
                            role="button",
                            cls="outline thin",
                        ),
                        A(
                            event.start.year,
                            href=f"/event/year/{event.isodate(month=False, day=False)}",
                            role="button",
                            cls="outline thin",
                        ),
                        A(
                            f"w{event.week}",
                            href=f"/event/week/{event.isodate(week=True)}",
                            role="button",
                            cls="outline thin",
                        ),
                        cls="right",
                    ),
                    cls=f"grid {event.category}",
                    title=event.category.capitalize(),
                ),
            ),
            (
                Card(
                    Header("Subevents"),
                    (
                        get_vertical_display(event.start, event.end, subevents)
                        if len(items.Duration(event.end - event.start)) > 24 * 60
                        else get_day_display(event.start, event.end, subevents)
                    ),
                )
                if subevents
                else ""
            ),
            (
                components.get_items_display(superevents, title="Overlaps")
                if superevents
                else ""
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
    duration = event.duration
    return (
        *components.get_header_item_edit(event),
        Main(
            Form(
                components.get_title_input(event.title),
                get_period_edit(
                    event.date,
                    event.time,
                    event.end_date,
                    event.end_time,
                    weeks=duration.weeks,
                    days=duration.days,
                    hours=duration.hours,
                    minutes=duration.minutes,
                ),
                Label(
                    "Category",
                    Select(
                        *[
                            Option(c, selected=c == event.category, cls=c)
                            for c in constants.EVENT_CATEGORIES
                        ],
                        name="category",
                    ),
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
    weeks: int = None,
    days: int = None,
    hours: int = None,
    minutes: int = None,
    tags: list[str] = None,
    category: str = None,
):
    "Actually edit the event."
    assert isinstance(event, items.Event)
    event.title = title
    event.text = text.strip()
    # Start date is always given.
    start = dt.datetime.fromisoformat(start_date)
    # Add start time, if given.
    if start_time:
        start = dt.datetime.combine(start, dt.time.fromisoformat(start_time))
    # Duration, if given.
    duration = items.Duration(weeks=weeks, days=days, hours=hours, minutes=minutes)
    # End datetime, if given.
    if end_date:
        end = dt.date.fromisoformat(end_date)
        # End time given.
        if end_time:
            end = dt.datetime.combine(end, dt.time.fromisoformat(end_time))
    else:
        end = None
    # Start datetime was changed.
    if start != event.start:
        # End datetime was not changed; start + duration, if given, else current.
        if end == event.end:
            if duration:
                end = start + duration.timedelta
            else:
                end = start + event.duration.timedelta
    # Neither start nor end datetime were changed; use duration, if given, else current.
    elif end == event.end:
        if duration:
            end = start + duration.timedelta
        else:
            end = start + event.duration.timedelta
    event.set(start, end)
    event.tags = tags
    event.category = category
    event.write()
    return components.redirect(event.url)


@rt("/{event:Item}/copy")
def get(event: items.Item):
    "Form for making a copy of the event."
    assert isinstance(event, items.Event)
    return (
        Title(f"Copy '{event}'"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Copy ", components.get_event_icon(), event),
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
def post(
    session,
    source: items.File,
    title: str,
):
    "Actually copy the event."
    assert isinstance(source, items.Event)
    event = items.Event()
    event.title = title
    event.set(source.start, source.end)
    event.category = source.category
    event.text = source.text
    event.tags = source.tags
    event.write()
    return components.redirect(f"{event.url}/edit")


@rt("/{event:Item}/recurring")
def get(event: items.Item):
    "Form for making recurring copies of the event."
    assert isinstance(event, items.Event)
    return (
        Title(f"Recurring '{event}'"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Create recurring ", components.get_event_icon(), event),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Legend("Recurring every..."),
                    Input(
                        type="radio", id="recurring_day", name="recurring", value="day"
                    ),
                    Label("Day", htmlFor="recurring_day"),
                    Input(
                        type="radio",
                        id="recurring_2day",
                        name="recurring",
                        value="2day",
                    ),
                    Label("Two days", htmlFor="recurring_2day"),
                    Input(
                        type="radio",
                        id="recurring_week",
                        name="recurring",
                        value="week",
                    ),
                    Label("Week", htmlFor="recurring_week"),
                    Input(
                        type="radio",
                        id="recurring_2week",
                        name="recurring",
                        value="2week",
                    ),
                    Label("Two weeks", htmlFor="recurring_2week"),
                    Input(
                        type="radio",
                        id="recurring_month",
                        name="recurring",
                        value="month",
                    ),
                    Label("Month", htmlFor="recurring_month"),
                    Input(
                        type="radio",
                        id="recurring_2month",
                        name="recurring",
                        value="2month",
                    ),
                    Label("Two months", htmlFor="recurring_2month"),
                    Input(
                        type="radio",
                        id="recurring_3month",
                        name="recurring",
                        value="3month",
                    ),
                    Label("Three months", htmlFor="recurring_3month"),
                    Input(
                        type="radio",
                        id="recurring_year",
                        name="recurring",
                        value="year",
                    ),
                    Label("Year", htmlFor="recurring_year"),
                ),
                Fieldset(
                    Label(
                        "After",
                        Input(type="date", value=event.date, disabled=True),
                    ),
                    Label(
                        "Last day",
                        Input(type="date", name="last_date"),
                    ),
                    Label(
                        "Number of times",
                        Input(type="number", name="number", min=1, step=1),
                    ),
                    cls="grid",
                ),
                Input(type="submit", value="Create events"),
                action=f"{event.url}/recurring",
                method="POST",
            ),
            components.get_cancel_form(event.url),
            cls="container",
        ),
    )


@rt("/{source:Item}/recurring")
def post(
    session,
    source: items.File,
    recurring: str = None,
    last_date: str = None,
    number: int = 0,
):
    "Actually create the recurring events."
    assert isinstance(source, items.Event)
    number = number or None  # Zero means 'no value given'.
    if last_date:
        end = dt.datetime.combine(dt.date.fromisoformat(last_date), dt.time())
    else:
        end = None
    days = None
    months = None
    match recurring:
        case "day":
            days = dt.timedelta(days=1)
        case "2day":
            days = dt.timedelta(days=2)
        case "week":
            days = dt.timedelta(days=7)
        case "2week":
            days = dt.timedelta(days=14)
        case "month":
            months = 1
        case "2month":
            months = 2
        case "3month":
            months = 3
        case "year":
            months = 12
        case _:
            raise NotImplementedError

    start = copy.copy(source.start)
    month = start.month
    year = start.year
    starts = []
    while True:
        if days:
            start = start + days
        else:
            month += months
            if month > 12:
                month = month % 12
                year += 1
            day = source.start.day  # Original day used if possible.
            while True:  # Watch out for shorter months.
                try:
                    start = dt.datetime(
                        year, month, day, hour=start.hour, minute=start.minute
                    )
                except ValueError:  # No such day in that month and year.
                    day -= 1
                else:
                    break
        if end is not None and start > end:
            break
        if number is not None and (number := number - 1) < 0:
            break
        starts.append(start)

    timedelta = source.end - source.start
    for start in starts:
        event = items.Event()
        event.title = source.title
        event.set(start, start + timedelta)
        event.text = f"{source.text}\n\nRecurring copy of [[{source.id}]]."
        event.tags = source.tags
        event.category = source.category
        event.write()
    add_toast(session, f"Created {len(starts)} recurring events.", "success")
    return components.redirect(source.url)


@rt("/{event:Item}/delete")
def get(event: items.Item):
    "Ask for confirmation to delete the event."
    assert isinstance(event, items.Event)
    return (
        *components.get_header_item_delete(event),
        Main(
            H3("Really delete the event?"),
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
    start = dt.datetime(year, 1, 1)
    end = dt.datetime(year + 1, 1, 1)
    events = [e for e in items.get_items("event") if e.overlap_days(start, end)]
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
    events = [e for e in items.get_items("event") if e.overlap(first, last)]
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
    start = dt.datetime.strptime(f"{year}-{week}-1", "%G-%V-%u")
    try:
        end = dt.datetime.strptime(f"{year}-{week+1}-1", "%G-%V-%u")
    except ValueError:
        end = dt.datetime.strptime(f"{year+1}-{1}-1", "%G-%V-%u")
    prev = start - dt.timedelta(days=4)  # Thursday previous week.
    next = end + dt.timedelta(days=3)  # Thursday next week.
    events = [e for e in items.get_items("event") if e.overlap(start, end)]
    weekdays = [start + dt.timedelta(days=day) for day in range(7)]
    thursday = weekdays[3]
    today_ordinal = dt.datetime.now().toordinal()
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
                            cls="outline thin",
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
    events = [e for e in items.get_items("event") if e.overlap(thisday, next)]
    beyond_thisday = sorted(
        [e for e in events if not e.within(thisday, next)],
        key=lambda e: len(e),
        reverse=True,
    )
    # Then thisdays events, sorted by start time.
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
                            cls="outline thin",
                        ),
                        A(
                            year,
                            href=f"/event/year/{year}",
                            role="button",
                            cls="outline thin",
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
                (get_day_display(thisday, next, events) if events else I("No events")),
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


def get_period_edit(
    start_date=None,
    start_time=None,
    end_date=None,
    end_time=None,
    weeks=None,
    days=None,
    hours=None,
    minutes=None,
):
    return Div(
        Div(
            Label(
                "Start date",
                Input(
                    type="date",
                    name="start_date",
                    value=start_date or dt.date.today(),
                    required=True,
                ),
            ),
            Label(
                "Start time",
                Input(
                    type="time",
                    name="start_time",
                    value=start_time,
                ),
            ),
            Label(
                "End date",
                Input(
                    type="date",
                    name="end_date",
                    value=end_date,
                ),
            ),
            Label(
                "End time",
                Input(
                    type="time",
                    name="end_time",
                    value=end_time,
                ),
            ),
            cls="grid",
        ),
        Div(
            Label(
                "Weeks",
                Input(
                    type="number",
                    name="weeks",
                    value=weeks or None,
                    step=1,
                    min=0,
                ),
            ),
            Label(
                "Days",
                Input(
                    type="number",
                    name="days",
                    value=days or None,
                    step=1,
                    min=0,
                ),
            ),
            Label(
                "Hours",
                Input(
                    type="number",
                    name="hours",
                    value=hours or None,
                    step=1,
                    min=0,
                    max=23,
                ),
            ),
            Label(
                "Minutes",
                Input(
                    type="nuber",
                    name="minutes",
                    value=minutes or None,
                    step=1,
                    min=0,
                    max=60,
                ),
            ),
            cls="grid",
        ),
    )


def get_month_table(year, month, events, full=True):
    "Generate the display the given events of a specified month."
    today_ordinal = dt.datetime.now().toordinal()
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
    events = set(events)
    while events:
        cells = []
        next_events = get_next_events_day(events, start, end)
        events = set(events).difference(next_events)
        sum_colspan = 0
        for event in next_events:
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
            cells.append(
                Td(
                    (
                        get_event_display_basic(event, start, end)
                        if full
                        else get_event_display_minimal(event, start, end)
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


def get_vertical_display(start, end, events):
    "Display the events vertically."
    days = [
        dt.datetime.fromordinal(d) for d in range(start.toordinal(), end.toordinal())
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
    events = set(events)  # Make copy to avoid changing incoming argument.
    while events:
        next_events = get_next_events_day(events, start, end)
        events = set(events).difference(next_events)
        for event in next_events:
            for slot, day in enumerate(days):
                if day.toordinal() == event.start.toordinal():
                    rows[slot].append(
                        Td(
                            get_event_display_standard(event, start, end),
                            rowspan=event.days,
                        )
                    )
    return Table(*[Tr(*row) for row in rows], cls="vertical")


def get_day_display(start, end, events):
    "Display the events of the day vertically."
    # Desired side-effect; makes copy, which avoids changing the incoming argument.
    entire_day_events = [e for e in events if e.whole_days]
    part_day_events = set(events).difference(entire_day_events)

    # Part-day events, if any.
    colspan = 0
    if part_day_events:
        try:
            first = min([e.start for e in part_day_events])
            first_hour = min(first.hour, 7)
        except ValueError:  # No values to get min for.
            first_hour = 7
        try:
            last = max([e.end for e in part_day_events])
            last_hour = max(last.hour, 18) + 1
        except ValueError:  # No values to get max for.
            last_hour = 19
        hours = [
            dt.datetime.combine(
                dt.date(start.year, start.month, start.day),
                dt.time(hour=h),
            )
            for h in range(first_hour, last_hour)
        ]
        rows = [
            [
                Th(
                    hour.strftime("%H:%M"),
                    cls="night" if (hour.hour <= 6 or hour.hour >= 19) else None,
                )
            ]
            for hour in hours
        ]
        while part_day_events:
            colspan += 1
            next_events = get_next_events_hour(part_day_events, start, end)
            part_day_events = set(part_day_events).difference(next_events)
            for event in next_events:
                for slot, hour in enumerate(hours):
                    if hour.hour == event.start.hour:
                        rows[slot].append(
                            Td(
                                get_event_display_full(
                                    event, start, end, vertical=True
                                ),
                                rowspan=max(
                                    1,
                                    math.floor(
                                        (event.end - hour).total_seconds() / 3600
                                    ),
                                ),
                            )
                        )
    else:
        rows = []

    # Prepend the entire-day events, if any.
    if entire_day_events:
        rows = (
            [
                Tr(
                    Th(rowspan=len(entire_day_events)),
                    Td(
                        get_event_display_full(entire_day_events[0], start, end),
                        colspan=colspan,
                    ),
                )
            ]
            + [
                Tr(
                    Td(
                        get_event_display_full(e, start, end),
                        colspan=max(1, colspan),
                    )
                )
                for e in entire_day_events[1:]
            ]
            + rows
        )
    return Table(*[Tr(*row) for row in rows], cls="vertical")


def get_next_events_day(events, start, end):
    "Return the next sorted list of non-overlapping events day-wise."
    covers_period = [e for e in events if e.start <= start and e.end >= end]
    if covers_period:
        covers_period.sort()
        return [covers_period[0]]
    events = sorted(events)
    result = []
    for event in events:
        for e in result:
            if event.overlap_days(e.start, e._end):
                break
        else:
            result.append(event)
    return result


def get_next_events_hour(events, start, end):
    "Return the next sorted list of non-overlapping events hour-wise."
    non_overlapping = get_non_overlapping_hours(events)
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
    events = sorted(events)
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


def get_event_display_minimal(event, start, end):
    "Return a minimal event display."
    return A(
        Div(cls="vspacer " + get_event_classes(event, start, end)),
        href=event.url,
        title=f"{event.category.capitalize()}: {event.title}",
        cls="black",
    )


def get_event_display_basic(event, start, end):
    "Return a basic event display."
    return Div(
        get_event_link(event, event.title),
        title=f"{event.display(year=start.year)}: {event.category.capitalize()}",
        cls=get_event_classes(event, start, end),
    )


def get_event_display_standard(event, start, end):
    "Return a standard event display."
    return Div(
        get_event_link(event, f"{event.display(year=start.year)}: {event.title}"),
        title=event.category.capitalize(),
        cls=get_event_classes(event, start, end),
    )


def get_event_display_full(event, start, end, vertical=False):
    "Return the display of the event at different levels of information."
    return Div(
        get_event_link(event, f"{event.display(year=start.year)}: {event.title}"),
        Br(),
        NotStr(markdown.to_html(event.text)),
        title=event.category.capitalize(),
        cls=get_event_classes(event, start, end, vertical=vertical),
    )


def get_event_link(event, title):
    return A(title, href=event.url, cls="black")


def get_event_classes(event, start, end, vertical=False):
    "Get the event classes; border and category."
    if event.duration < items.Duration(days=1):
        border = "border-open"
    elif event.start < start:
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
