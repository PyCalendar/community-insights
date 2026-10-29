"""How fast the pages and images of a running site load again while the data is the same.

    make run                                    # in another terminal
    make benchmark SCOPE=3                      # the project 3, as admin@example.com
    make benchmark SCOPE=collective~icalendar   # a public scope

Each page of the scope is loaded twice, and so is each image and chart data it shows. The
second load counts. An image is also asked for with its ETag, as a browser does
(``If-None-Match``). Every second load has to be faster than LIMIT.

On Linux it also shows how much each request raised the peak memory (RSS) of the server:
before each request the peak of its processes is reset (``/proc/PID/clear_refs``), after it
the peak (``VmHWM``) is read. The processes are those whose command line has ``--server``
(``runserver`` by default; ``gunicorn`` for the image).
"""

import argparse
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

LIMIT = 1.0  # seconds
PAGES = ["", "contributors/", "items/", "compare/"]
PEOPLE = 3  # pages of people, the first ones linked from the overview
PROC = Path("/proc")


class Links(HTMLParser):
    """The images, chart data, pages of people and form fields of a page.

    Args:
        base: The address of the page.
    """

    def __init__(self, base: str):
        """Read a page of the address.

        Args:
            base: The address of the page.
        """
        super().__init__()
        self.base = base
        self.images: list[str] = []
        self.people: list[str] = []
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        """Note what the element links.

        Args:
            tag: The name of the element.
            attrs: Its attributes.
        """
        found = {name: value or "" for name, value in attrs}
        if tag == "img" and found.get("src"):
            self.images.append(urljoin(self.base, found["src"]))
        if found.get("data-chart-json"):
            self.images.append(urljoin(self.base, found["data-chart-json"]))
        if tag == "a" and "/people/" in found.get("href", ""):
            self.people.append(urljoin(self.base, found["href"]))
        if tag == "input" and found.get("name"):
            self.fields[found["name"]] = found.get("value", "")


def same_site(url: str, base: str) -> bool:
    """Whether the address is on the site, and no static file.

    Args:
        url: The address.
        base: The address of the site.

    Returns:
        True for a page or image the site draws.

    Examples:
        >>> same_site("http://localhost:5000/s/3/chart/hours.svg", "http://localhost:5000")
        True
        >>> same_site("http://localhost:5000/static/logo.svg", "http://localhost:5000")
        False
        >>> same_site("https://avatars.githubusercontent.com/u/1", "http://localhost:5000")
        False
    """
    parts = urlsplit(url)
    return parts.netloc == urlsplit(base).netloc and not parts.path.startswith("/static/")


def unique(urls: list[str]) -> list[str]:
    """The addresses in their order, each once.

    Args:
        urls: The addresses.

    Returns:
        The addresses without repetitions.

    Examples:
        >>> unique(["a", "b", "a"])
        ['a', 'b']
    """
    return list(dict.fromkeys(urls))


def server_processes(name: str, proc: Path = PROC) -> list[Path]:
    """The processes of the server that this user may watch.

    Args:
        name: A part of their command line, such as ``runserver``.
        proc: The directory of the processes.

    Returns:
        Their directories in ``/proc``; none if they cannot be read.
    """
    found = []
    for directory in proc.glob("[0-9]*"):
        try:
            command = (directory / "cmdline").read_bytes().replace(b"\0", b" ").decode()
            if name in command and "site_speed" not in command:
                (directory / "status").read_text()
                found.append(directory)
        except OSError:
            continue
    return found


def kilobytes(status: str, field: str) -> int:
    """A size of ``/proc/PID/status``.

    Args:
        status: The text of the file.
        field: Such as ``VmHWM``, the peak of the memory, or ``VmRSS``, the memory now.

    Returns:
        The size in kB; 0 if it is not there.

    Examples:
        >>> kilobytes("Name:\\tpython\\nVmHWM:\\t  204800 kB\\n", "VmHWM")
        204800
        >>> kilobytes("Name:\\tpython\\n", "VmHWM")
        0
    """
    for line in status.splitlines():
        if line.startswith(field + ":"):
            return int(line.split()[1])
    return 0


def reset_peaks(processes: list[Path]) -> dict[Path, int]:
    """Reset the peaks of the memory to what the processes use now.

    Args:
        processes: Their directories in ``/proc``.

    Returns:
        The memory now of each, in kB.
    """
    now = {}
    for directory in processes:
        try:
            (directory / "clear_refs").write_text("5")
            now[directory] = kilobytes((directory / "status").read_text(), "VmRSS")
        except OSError:
            continue
    return now


def peak_increase(before: dict[Path, int]) -> int:
    """How much more memory the processes used at their peak than before, the most of them.

    Args:
        before: The memory before, from reset_peaks.

    Returns:
        The increase in kB.
    """
    increase = 0
    for directory, used in before.items():
        try:
            peak = kilobytes((directory / "status").read_text(), "VmHWM")
        except OSError:
            continue
        increase = max(increase, peak - used)
    return increase


def timed(
    client: httpx.Client, url: str, processes: list[Path], **headers
) -> tuple[float, int, httpx.Response]:
    """Load an address and measure the time and the peak memory of the server.

    Args:
        client: The client, signed in.
        url: The address.
        processes: The processes of the server.
        **headers: Headers of the request.

    Returns:
        The seconds, the increase of the peak memory in kB, and the response.
    """
    before = reset_peaks(processes)
    start = time.perf_counter()
    response = client.get(url, headers=headers)
    return time.perf_counter() - start, peak_increase(before), response


def sign_in(client: httpx.Client, base: str, email: str, password: str) -> None:
    """Sign in with the form of the site.

    Args:
        client: The client.
        base: The address of the site.
        email: The email address.
        password: The password.

    Raises:
        SystemExit: If the site did not sign in.
    """
    page = client.get(f"{base}/accounts/login/")
    form = Links(str(page.url))
    form.feed(page.text)
    answer = client.post(
        f"{base}/accounts/login/",
        data={
            "csrfmiddlewaretoken": form.fields.get("csrfmiddlewaretoken", ""),
            "login": email,
            "password": password,
        },
        headers={"Referer": f"{base}/accounts/login/"},
    )
    if "/accounts/login/" in str(answer.url):
        raise SystemExit(f"Could not sign in as {email}")


def measure(
    base: str, scope: str, email: str, password: str, processes: list[Path]
) -> list[tuple[str, float, float, int]]:
    """Load each page and image twice; images also with their ETag.

    Args:
        base: The address of the site.
        scope: The scope, such as ``3`` or ``collective~icalendar``.
        email: The email address to sign in with; empty for a visitor.
        password: The password.
        processes: The processes of the server, to watch their memory.

    Returns:
        The address, the seconds of the first and of the second load, and the most the peak
        memory of the server rose in kB; the slowest second load first.
    """
    found = []

    def twice(url):
        """Load the address twice and note the times; the second response.

        Args:
            url: The address.

        Returns:
            The second response.
        """
        first, memory, response = timed(client, url, processes)
        response.raise_for_status()
        second, again, response = timed(client, url, processes)
        found.append((url, first, second, max(memory, again)))
        return response

    with httpx.Client(follow_redirects=True, timeout=300) as client:
        if email:
            sign_in(client, base, email, password)
        pages = [f"{base}/s/{scope}/{page}" for page in PAGES]
        images: list[str] = []
        index = 0
        while index < len(pages):
            response = twice(pages[index])
            index += 1
            links = Links(str(response.url))
            links.feed(response.text)
            images += [image for image in links.images if same_site(image, base)]
            people = [url for url in unique(links.people) if url not in pages]
            pages += people[: max(0, PEOPLE - sum("/people/" in url for url in pages))]
        for url in unique(images):
            response = twice(url)
            etag = response.headers.get("ETag")
            if etag:
                again, memory, answer = timed(client, url, processes, **{"If-None-Match": etag})
                found.append((f"{url}  (ETag: {answer.status_code})", 0.0, again, memory))
    return sorted(found, key=lambda row: -row[2])


def main(arguments: list[str] | None = None) -> int:
    """Print the times and whether every second load is faster than LIMIT.

    Args:
        arguments: The command line, without the name of the program.

    Returns:
        0 if every second load is faster than LIMIT, else 1.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--scope", default="3")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--limit", type=float, default=LIMIT)
    parser.add_argument("--server", default="runserver", help="a part of its command line")
    args = parser.parse_args(arguments)
    processes = server_processes(args.server)
    rows = measure(args.url.rstrip("/"), args.scope, args.email, args.password, processes)
    print(f"{'first':>8} {'again':>8} {'memory':>9}  address")
    for url, first, second, memory in rows:
        print(f"{first:8.3f} {second:8.3f} {memory / 1024:6.0f} MB  {url.removeprefix(args.url)}")
    slow = [row for row in rows if row[2] >= args.limit]
    most = max((row[3] for row in rows), default=0)
    print(f"{len(rows)} loads, {len(slow)} slower than {args.limit} s on the second load")
    if processes:
        print(f"the peak memory of the server rose by at most {most / 1024:.0f} MB")
    else:
        print(f"no process of the server with {args.server!r} found: memory not measured")
    return 1 if slow else 0


if __name__ == "__main__":
    sys.exit(main())
