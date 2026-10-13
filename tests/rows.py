"""A contributor row with every field, for the tests."""

BLANK = {
    "user_handle": "", "user_association": "", "commits_total": 0,
    "prs_total": 0, "prs_open": 0, "prs_merged": 0, "prs_unmerged": 0,
    "prs_commented": 0, "prs_reviewed": 0, "prs_approved": 0,
    "prs_changes_requested": 0, "issues_opened": 0, "issues_open": 0,
    "issues_commented": 0, "comments_total": 0, "actions_merges": 0,
    "actions_closes": 0, "actions_labels": 0, "days_to_merge": None,
    "months_active": 0, "date_first": None, "date_last": None,
}  # fmt: skip


def blank(**fields):
    return BLANK | fields
