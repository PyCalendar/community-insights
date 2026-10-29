"""The helpers of make benchmark (site_speed.py), without a server: /proc is faked."""

from tests.performance import site_speed

PAGE = """
<img src="/s/3/chart/hours.svg?theme=light" data-chart-src="/s/3/chart/hours.svg"
     data-chart-json="/s/3/chart/hours.json">
<img src="https://avatars.githubusercontent.com/u/1">
<a href="/s/3/people/bob/">bob</a> <a href="/s/3/items/">items</a>
<input name="csrfmiddlewaretoken" value="secret"> <input type="submit">
"""


def test_the_links_of_a_page():
    """Images, chart data, people and form fields are found."""
    links = site_speed.Links("http://localhost:5000/s/3/")
    links.feed(PAGE)
    assert links.images == [
        "http://localhost:5000/s/3/chart/hours.svg?theme=light",
        "http://localhost:5000/s/3/chart/hours.json",
        "https://avatars.githubusercontent.com/u/1",
    ]
    assert links.people == ["http://localhost:5000/s/3/people/bob/"]
    assert links.fields == {"csrfmiddlewaretoken": "secret"}


def process(proc, pid, command, rss, peak):
    """A fake process in the fake /proc."""
    directory = proc / str(pid)
    directory.mkdir()
    (directory / "cmdline").write_bytes(command.replace(" ", "\0").encode())
    (directory / "status").write_text(f"Name:\tpython\nVmHWM:\t{peak} kB\nVmRSS:\t{rss} kB\n")
    (directory / "clear_refs").write_text("")
    return directory


def test_the_processes_of_the_server(tmp_path):
    """The processes with the name in their command line, not the benchmark itself."""
    server = process(tmp_path, 10, "python manage.py runserver 5000", 1000, 2000)
    process(tmp_path, 11, "python -m tests.performance.site_speed --server runserver", 1, 1)
    process(tmp_path, 12, "nginx", 1, 1)
    (tmp_path / "self").mkdir()
    assert site_speed.server_processes("runserver", tmp_path) == [server]
    assert site_speed.server_processes("gunicorn", tmp_path) == []


def test_the_peak_of_the_memory(tmp_path):
    """The peak is reset to the memory now; the increase is the most of the processes."""
    first = process(tmp_path, 10, "gunicorn", 1000, 5000)
    second = process(tmp_path, 11, "gunicorn", 2000, 2000)
    before = site_speed.reset_peaks([first, second])
    assert before == {first: 1000, second: 2000}
    assert (first / "clear_refs").read_text() == "5"
    (second / "status").write_text("VmHWM:\t2500 kB\nVmRSS:\t2000 kB\n")
    (first / "status").write_text("VmHWM:\t1100 kB\nVmRSS:\t1000 kB\n")
    assert site_speed.peak_increase(before) == 500


def test_a_process_that_ended_is_left_out(tmp_path):
    """A worker that ended in between does not stop the measurement."""
    gone = tmp_path / "99"
    assert site_speed.reset_peaks([gone]) == {}
    assert site_speed.peak_increase({gone: 1000}) == 0


def test_the_result(monkeypatch, capsys):
    """Slower than the limit on the second load fails; the first load does not count."""
    rows = [("/s/3/", 5.0, 0.4, 2048), ("/s/3/chart/hours.svg", 0.1, 0.05, 0)]
    monkeypatch.setattr(site_speed, "measure", lambda *args: rows)
    monkeypatch.setattr(site_speed, "server_processes", lambda name: [])
    assert site_speed.main([]) == 0
    out = capsys.readouterr().out
    assert "2 loads, 0 slower than 1.0 s" in out
    assert "memory not measured" in out
    assert site_speed.main(["--limit", "0.3"]) == 1
