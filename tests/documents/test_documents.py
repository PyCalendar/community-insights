"""Documents made in the background, with their progress, and the messages of an account."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights import documents
from community_insights.models import Document, Message

pytestmark = pytest.mark.django_db


def started(browser, url):
    """The document a download starts, from the address it leads to."""
    response = browser.get(url)
    assert response.status_code == 302, url
    return Document.objects.get(pk=int(response["Location"].strip("/").split("/")[1]))


def test_an_ods_is_made_in_the_background_and_told_by_a_message(world, signed_in):
    """An ods is made in the background and told by a message."""
    pk = world["project"].pk
    document = started(signed_in, f"/s/{pk}/data/responses.ods?last=30")
    assert document.status == Document.DONE and document.progress == 100
    assert document.parameters == {"last": "30"}, "the time range is kept"
    assert document.user == world["user"] and document.path().is_file()
    page = signed_in.get(f"/documents/{document.pk}/").content.decode()
    assert "The file is ready." in page and f"/documents/{document.pk}/download/" in page
    progress = signed_in.get(f"/documents/{document.pk}/progress.json").json()
    assert progress == {
        "status": "done",
        "progress": 100,
        "message": "",
        "download": f"/documents/{document.pk}/download/",
    }
    message = Message.objects.get(user=world["user"])
    assert message.unread and message.title == f"responses-{pk}.ods is ready to download"
    assert message.link == f"/documents/{document.pk}/"


def test_the_messages_are_read_and_unread(world, signed_in):
    """The messages are read and unread."""
    signed_in.get(f"/s/{world['project'].pk}/data/commits.ods")
    menu = signed_in.get("/dashboard/").content.decode()
    assert 'title="unread">1</span>' in menu
    inbox = signed_in.get("/messages/").content.decode()
    assert "is ready to download" in inbox and ">new<" in inbox
    message = Message.objects.get()
    opened = signed_in.get(f"/messages/{message.pk}/")
    assert opened["Location"] == message.link
    message.refresh_from_db()
    assert not message.unread
    assert 'title="unread"' not in signed_in.get("/dashboard/").content.decode()
    Message.objects.create(user=world["user"], title="other", link="https://evil.example/")
    other = Message.objects.get(title="other")
    assert signed_in.get(f"/messages/{other.pk}/")["Location"] == "/messages/"
    Message.objects.create(user=world["user"], title="more")
    signed_in.post("/messages/read/")
    assert not Message.objects.filter(read_at__isnull=True).exists()


def test_documents_and_messages_are_private(world, signed_in, client):
    """Documents and messages are private."""
    from django.contrib.auth import get_user_model

    document = started(signed_in, f"/s/{world['project'].pk}/data/commits.ods")
    message = Message.objects.get()
    other = get_user_model().objects.create_user("o", "o@example.org", "pw")
    client.force_login(other)
    for url in (
        f"/documents/{document.pk}/",
        f"/documents/{document.pk}/progress.json",
        f"/documents/{document.pk}/download/",
        f"/messages/{message.pk}/",
    ):
        assert client.get(url).status_code == 404, url
    client.logout()
    assert client.get(f"/documents/{document.pk}/").status_code == 404
    assert client.get("/messages/").status_code == 302, "to the sign in"


def test_visitors_get_their_documents_by_their_session(world, client):
    """Visitors get their documents by their session."""
    document = started(client, "/s/o~r/contributors.ods?where=prs_total+%3E+0")
    assert document.user is None and document.session_key
    assert document.kind == Document.QUERY and document.status == Document.DONE
    download = client.get(f"/documents/{document.pk}/download/")
    assert download.status_code == 200 and b"".join(download.streaming_content)
    assert not Message.objects.exists(), "visitors have no messages"
    from django.test import Client

    assert Client().get(f"/documents/{document.pk}/").status_code == 404, "another visitor"


def test_a_query_with_a_mistake_is_told_at_once(world, signed_in):
    """A query with a mistake is told at once."""
    pk = world["project"].pk
    response = signed_in.get(f"/s/{pk}/contributors.ods?where=nonsense", follow=True)
    assert b"There is no variable" in response.content
    assert not Document.objects.exists()


def test_a_document_that_fails_says_why(world, signed_in, monkeypatch):
    """A document that fails says why."""

    def broken(*args, **kwargs):
        """Fail like a full disk."""
        raise RuntimeError("the disk is full")

    monkeypatch.setattr("community_insights.spreadsheet.to_ods", broken)
    document = started(signed_in, f"/s/{world['project'].pk}/data/commits.ods")
    assert document.status == Document.FAILED and document.error_code == "UnexpectedError"
    page = signed_in.get(f"/documents/{document.pk}/").content.decode()
    assert "The file could not be made." in page
    assert signed_in.get(f"/documents/{document.pk}/download/")["Location"] == (
        f"/documents/{document.pk}/"
    )
    assert "could not be made" in Message.objects.get().title


def test_the_progress_goes_up_with_the_sheets(world, signed_in, monkeypatch):
    """The progress goes up with the sheets."""
    seen = []
    original = documents.sheets_of

    def watched(document, step):
        """Make the sheets and note each step of the progress."""

        def noting(done, total):
            """Note a step of the progress and pass it on."""
            seen.append((done, total))
            step(done, total)

        return original(document, noting)

    monkeypatch.setattr(documents, "sheets_of", watched)
    started(signed_in, f"/s/{world['project'].pk}/data/responses.ods")
    assert seen == [(1, 4), (2, 4), (3, 4)], "responses, items, events, then the file"


def test_old_documents_are_deleted_with_their_files(world, signed_in):
    """Old documents are deleted with their files."""
    document = started(signed_in, f"/s/{world['project'].pk}/data/commits.ods")
    assert documents.clean_up() == 0
    assert documents.clean_up(timezone.now() + timedelta(days=8)) == 1
    assert not document.path().exists() and not Document.objects.exists()
    assert signed_in.get(f"/documents/{document.pk}/").status_code == 404


def test_a_deleted_file_is_not_found(world, signed_in):
    """A deleted file is not found."""
    document = started(signed_in, f"/s/{world['project'].pk}/data/commits.ods")
    document.path().unlink()
    assert signed_in.get(f"/documents/{document.pk}/download/").status_code == 404


def test_documents_run_in_a_thread_outside_of_tests(world, rf, settings, monkeypatch, user):
    """Documents run in a thread outside of tests."""
    settings.FETCH_WORKER = "internal"
    threads = []

    class Thread:
        """A thread that only notes how it was started."""

        def __init__(self, target, args, daemon, name):
            """Note the arguments of the thread."""
            threads.append((target, args, daemon, name))

        def start(self):
            """Start nothing."""
            pass

    monkeypatch.setattr("community_insights.documents.threading.Thread", Thread)
    monkeypatch.setattr(
        "community_insights.documents.transaction.on_commit", lambda function: function()
    )
    request = rf.get("/")
    request.user = user
    document = documents.start(request, Document.TABLE, "commits", "o~r", {}, "c.ods")
    assert document.status == Document.QUEUED
    assert threads == [(documents.run_in_thread, (document.pk,), True, "document")]


def test_the_thread_makes_the_document(world, user, rf, monkeypatch):
    """The thread makes the document."""
    request = rf.get("/")
    request.user = user
    monkeypatch.setattr("community_insights.documents.close_old_connections", lambda: None)
    document = Document.objects.create(user=user, table="commits", scope="o~r", filename="c.ods")
    documents.run_in_thread(document.pk)
    document.refresh_from_db()
    assert document.status == Document.DONE


def test_htmx_shows_the_state_of_a_document(world, signed_in):
    """While a document is made, htmx asks every second; when ready, the download shows."""
    pk = world["project"].pk
    document = started(signed_in, f"/s/{pk}/data/responses.ods")
    htmx = {"HTTP_HX_REQUEST": "true"}
    ready = signed_in.get(f"/documents/{document.pk}/progress.json", **htmx).content.decode()
    assert ready.lstrip().startswith('<div class="card-body" id="document-state"')
    assert "hx-get" not in ready and f"/documents/{document.pk}/download/" in ready
    Document.objects.filter(pk=document.pk).update(status=Document.RUNNING, progress=40)
    running = signed_in.get(f"/documents/{document.pk}/progress.json", **htmx).content.decode()
    assert 'hx-trigger="every 1s"' in running and "40 %" in running
    assert "/download/" not in running
    page = signed_in.get(f"/documents/{document.pk}/").content.decode()
    assert f'hx-get="/documents/{document.pk}/progress.json"' in page
    assert "document-progress.js" not in page


def test_htmx_shows_why_a_document_failed(world, signed_in):
    """A failed document shows its message and what to do, and is not asked again."""
    pk = world["project"].pk
    document = started(signed_in, f"/s/{pk}/data/responses.ods")
    Document.objects.filter(pk=document.pk).update(
        status=Document.FAILED, message="broken", error_code="GitHubUnreachable"
    )
    page = signed_in.get(
        f"/documents/{document.pk}/progress.json", HTTP_HX_REQUEST="true"
    ).content.decode()
    assert "The file could not be made." in page and "broken" in page
    assert "What to do" in page and "hx-get" not in page
