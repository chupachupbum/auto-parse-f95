"""Parse f95zone thread pages to extract game metadata."""

import re
from dataclasses import dataclass

import cloudscraper
from bs4 import BeautifulSoup

# Known engine tags on f95zone
KNOWN_ENGINES = [
    "QSP", "RPGM", "Unity", "HTML", "RAGS", "Java",
    "Ren'Py", "Flash", "ADRIFT", "Tads", "Wolf RPG",
    "Unreal Engine", "WebGL", "Others",
]

# Tags that indicate the game is complete
COMPLETE_TAGS = ["Completed", "Abandoned"]

# Patterns that indicate the developer has other works
OTHER_WORK_PATTERNS = re.compile(
    r"other\s+(game|work|project)s?", re.IGNORECASE
)


@dataclass
class GameInfo:
    """Parsed game information from an f95zone thread."""
    name: str
    version: str
    developer: str
    engine: str
    complete: bool
    other_work: bool
    link: str


def fetch_page(url: str) -> str:
    """Fetch the HTML content of an f95zone thread page."""
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_title(h1_element) -> tuple[str, str, str]:
    """Parse game name, version, and developer from the h1 title element.

    Title format after stripping labels: Game Name [vX.X] [Developer]
    """
    # Remove all label/tag spans to get plain title text
    for label in h1_element.find_all("span", class_="label"):
        label.decompose()
    for link in h1_element.find_all("a", class_="labelLink"):
        link.decompose()

    raw_title = h1_element.get_text(strip=True)

    # Extract bracketed parts: [vX.X.X] and [Developer]
    brackets = re.findall(r"\[([^\]]+)\]", raw_title)

    version = ""
    developer = ""
    name = raw_title

    if brackets:
        # Find the version bracket (starts with v or contains a number pattern or final)
        for b in brackets:
            if re.match(r"v?\d", b, re.IGNORECASE) or b.lower().startswith("v") or "final" in b.lower():
                version = b
                break

        # Developer is typically the last bracket
        developer = brackets[-1]

        # Name is everything before the first bracket
        first_bracket_pos = raw_title.index("[")
        name = raw_title[:first_bracket_pos].strip()

    return name, version, developer


def parse_prefix_tags(soup: BeautifulSoup) -> list[str]:
    """Extract prefix tags (engine, status) from the title area."""
    h1 = soup.find("h1", class_="p-title-value")
    if not h1:
        return []

    tags = []
    for label_span in h1.find_all("span", class_="label"):
        tag_text = label_span.get_text(strip=True)
        if tag_text:
            tags.append(tag_text)
    return tags


def parse_title_tag_segments(soup: BeautifulSoup) -> list[str]:
    """Extract prefix segments from the HTML <title> tag as a fallback.

    Title format: 'Engine - Status - Game [v...] [dev] | F95zone | ...'
    Returns the dash-separated segments before '|'.
    """
    title_tag = soup.find("title")
    if not title_tag:
        return []

    title_text = title_tag.get_text(strip=True)
    # Take everything before the first '|' (the f95zone suffix)
    main_part = title_text.split("|")[0].strip()
    # Split by ' - ' to get segments like ['Engine', 'Status', 'Game [v] [dev]']
    segments = [s.strip() for s in main_part.split(" - ")]
    # The last segment is the game title, the preceding ones are prefix tags
    return segments[:-1] if len(segments) > 1 else []


def detect_engine(tags: list[str], fallback_tags: list[str] | None = None) -> str:
    """Detect the game engine from prefix tags.

    Tries the primary tags first, then falls back to title tag segments.
    """
    for tag_list in [tags, fallback_tags or []]:
        for tag in tag_list:
            for engine in KNOWN_ENGINES:
                if tag.lower() == engine.lower():
                    return engine
    return ""


def detect_complete(tags: list[str]) -> bool:
    """Check if the game is completed or abandoned."""
    for tag in tags:
        if tag in COMPLETE_TAGS:
            return True
    return False


def detect_other_work(soup: BeautifulSoup) -> bool:
    """Check if the developer has other works mentioned in the first post."""
    first_post = soup.select_one(".message-threadStart .bbWrapper")
    if not first_post:
        # Fallback: try first .bbWrapper
        first_post = soup.select_one(".bbWrapper")

    if not first_post:
        return False

    post_text = first_post.get_text()
    return bool(OTHER_WORK_PATTERNS.search(post_text))


def parse_html(html: str, url: str) -> GameInfo:
    """Parse the HTML content of an f95zone thread page.

    Args:
        html: The raw HTML string.
        url: The original URL (used for the link field).

    Returns:
        GameInfo dataclass with parsed data.
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract prefix tags before modifying the h1
    prefix_tags = parse_prefix_tags(soup)
    # Fallback: also extract segments from the <title> tag
    title_segments = parse_title_tag_segments(soup)

    # Parse title (this modifies the h1 element by removing labels)
    h1 = soup.find("h1", class_="p-title-value")
    if not h1:
        raise ValueError(
            "Could not find thread title on the page. "
            "The page may require login or the URL may be invalid."
        )

    name, version, developer = parse_title(h1)

    # Use prefix tags first, fall back to title tag segments for engine
    all_tags = prefix_tags or title_segments
    engine = detect_engine(prefix_tags, fallback_tags=title_segments)
    complete = detect_complete(all_tags)
    other_work = detect_other_work(soup)

    return GameInfo(
        name=name,
        version=version,
        developer=developer,
        engine=engine,
        complete=complete,
        other_work=other_work,
        link=url,
    )


def parse_f95_thread(url: str) -> GameInfo:
    """Parse an f95zone thread URL and return game information.

    Args:
        url: Full URL to an f95zone thread.

    Returns:
        GameInfo dataclass with parsed data.

    Raises:
        ValueError: If the URL is not a valid f95zone thread.
        ConnectionError: If the page cannot be fetched.
    """
    if "f95zone.to/threads/" not in url:
        raise ValueError(
            "URL must be an f95zone thread link (containing 'f95zone.to/threads/')"
        )

    html = fetch_page(url)
    return parse_html(html, url)
