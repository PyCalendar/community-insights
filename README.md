# gh-community

Contributor analysis for GitHub repositories, using PyGithub.

## Installation

- ```sh
  make install-dev
  ```

  link the local `.venv` (editable) for installation with shell completion

- ```sh
  make install
  ```

  use pipx (editable) for installation with shell completion

- ```sh
  make init
  ```

  initialize the local environment. All commands work with `uv run`.

## Token access

The token only needs **read** access to the analysed repositories:

| Case | Needed |
| ---- | ------ |
| Public repositories | No scopes; a token just raises the rate limit |
| Private repositories, classic token | `repo` scope |
| Private repositories, fine-grained token | Select the repositories; read-only *Pull requests* (*Metadata* read-only is added automatically) |
| GitHub Actions `GITHUB_TOKEN` | `permissions: pull-requests: read` and `contents: read` |

## Usage

### Contributor analysis

```sh
gh-community contributors all              # sorted by merged pull requests
gh-community contributors all --sort commits_total
gh-community contributors all owner/name other/repo --token ...  # overrides the config
```

Output is a Markdown table with right-aligned numbers (the default columns of
`gh-community result`, below). Some details of the numbers: the number of
comments does not matter for `issues_commented` and `prs_commented`, only on how
many issues or pull requests there is one (comments and comments on the changes
for pull requests, never on one's own). `days_last` is the newest activity in
the repositories: any of the data read: a commit, pull request, issue, comment,
review, commit comment or an action on an issue or pull request such as closing,
merging or labelling.

`--sort` takes a variable (below), `+variable` for ascending and `-variable` for
descending order (`--sort=-days_last`, or `--sort -days_last`). Without a sign
the handle and the `days_` variables are ascending (so the newest activity is
first) and the rest descending (the highest first); the default is `prs_merged`.
`user_association` is sorted by privilege. Ties are sorted by handle.

Progress and the API calls used are printed to stderr. Responses are cached in
`$TMPDIR/gh-community-cache-<uid>` using ETags: repeating an analysis only
downloads what changed, and requests answered with `304 Not Modified` do not
count against the rate limit. The first analysis of a repository needs one
request per contributor (latest commit) and one per pull request (reviews).
Reviews and latest commits are not even requested again while the pull request's
`updated_at` or the contributor's number of commits is the same.
`--no-cache` skips the cache, `--cache-dir` moves it. Pages and the per-contributor and
per-pull-request requests are sent in parallel (`--jobs`, default 4).

### Stored results

Every `contributors all` stores its result as `org-repo-yyyy-mm-dd-hh-mm-ss.csv`
(several repositories are joined with `_`) in the directory of the config file,
for later analysis; `--no-save` skips it. The CSV holds the raw numbers with the
names of the variables below (`date_first` and `date_last` as ISO dates). What
can be calculated from the columns is not stored, but can be used in
expressions: `prs_total`, `prs_closed`, `issues_closed`, `user_bot`, `days_first`
and `days_last`. Files from before the columns were renamed or existed can be
read, with 0 for what they lack.

```sh
gh-community result --list                # list the names of the stored results
gh-community result NAME                  # NAME completes with the shell completion
gh-community result NAME --columns user_handle+prs_merged+prs_open+days_first
gh-community result NAME --columns '+prs_open-commits_total'   # change the default
gh-community result NAME --sort=-days_last   # the oldest activity first
gh-community result NAME --csv --columns user_handle+prs_merged   # CSV, not a table
gh-community result NAME 'days_last < 30' # only those with activity in 30 days
gh-community result NAME --remove 'days_last > 90'   # the same, inverted: remove them
gh-community result NAME --remove 'prs_merged<10 and (days_last < 100 or issues_opened > 0)'
gh-community result NAME --remove '"[bot]" in user_handle'
```

The result is shown as a Markdown table, followed by a line such as
`Showing 3 of 10 contributors.`; the file is not changed. With `--csv` (also
for `contributors all`) it is printed as CSV instead, for the same columns,
filters and sorting: the header is the names of the columns as in the table (`merged PRs`, `last
activity`) and the values are
only numbers and strings, so the days are numbers (empty if unknown), `user_bot`
is 1 or 0 and there is no `X/total`; the line with the count goes to stderr. Names are grouped by
prefix, with the unit first (`days_`, `months_`), and have no aliases.

`--columns` takes the columns to show, split by `+` and `-`, never by a comma.
`a+b` shows exactly the columns a and b, in that order; a specification that
starts with a sign changes the default columns: `+x-y` adds x and removes y
(write `--columns=-y` if it starts with `-`). Columns complete, too. Columns and
variables have the same names. The pull request and
issue columns that are a part of the pull requests or issues opened show it as
`X/total`, for example `prs_merged` as `245/269`; the variable is the number.
`days_first` and `days_last` show the days ago, the variables the days.

Default columns:

| Column | Meaning |
| ------ | ------- |
| `user_handle` | text: the GitHub login |
| `commits_total` | commits in the contributors list |
| `prs_merged` | pull requests opened and merged, shown as X/prs_total (variable prs_merged: the number) |
| `issues_opened` | issues opened |
| `issues_commented` | issues of others commented on |
| `prs_commented` | pull requests of others commented on |
| `prs_reviewed` | pull requests of others reviewed |
| `days_last` | days ago of the last activity (variable days_last: the days) |

Additional columns:

| Column | Meaning |
| ------ | ------- |
| `actions_closes` | issues and pull requests closed by them, other than by merging |
| `actions_labels` | labels set by them |
| `actions_merges` | pull requests merged by them |
| `comments_total` | all comments written |
| `days_first` | days ago of the first activity (variable days_first: the days) |
| `days_to_merge` | median days until their pull requests were merged |
| `issues_closed` | issues opened and closed, shown as X/issues_opened (variable issues_closed: the number) |
| `issues_open` | issues opened and still open, shown as X/issues_opened (variable issues_open: the number) |
| `months_active` | months with any activity |
| `prs_approved` | pull requests of others approved |
| `prs_changes_requested` | pull requests of others with changes requested |
| `prs_closed` | pull requests opened and closed (merged + unmerged), shown as X/prs_total (variable prs_closed: the number) |
| `prs_open` | pull requests opened and still open, shown as X/prs_total (variable prs_open: the number) |
| `prs_total` | pull requests opened, in total |
| `prs_unmerged` | pull requests opened and closed without merging, shown as X/prs_total (variable prs_unmerged: the number) |
| `user_association` | text, always lowercase, ordered by privilege: owner > member > collaborator > contributor > first_timer > first_time_contributor > mannequin > none > empty; the most privileged seen |
| `user_bot` | True if the handle contains [bot] or is Copilot, else False |

An expression after the name shows only the contributors for which it is true;
`--remove` takes an expression too and removes those for which it is true (it
can be repeated). Both can be combined. The variables (also in
`gh-community result --help`):

| Variable | Meaning |
| -------- | ------- |
| `actions_closes` | issues and pull requests closed by them, other than by merging |
| `actions_labels` | labels set by them |
| `actions_merges` | pull requests merged by them |
| `comments_total` | all comments written |
| `commits_total` | commits in the contributors list |
| `days_first` | days since the first activity |
| `days_last` | days since the last activity |
| `days_to_merge` | median days until their pull requests were merged |
| `issues_closed` | issues opened and closed |
| `issues_commented` | issues of others commented on |
| `issues_open` | issues opened and still open |
| `issues_opened` | issues opened |
| `months_active` | months with any activity |
| `prs_approved` | pull requests of others approved |
| `prs_changes_requested` | pull requests of others with changes requested |
| `prs_closed` | pull requests opened and closed (merged + unmerged) |
| `prs_commented` | pull requests of others commented on |
| `prs_merged` | pull requests opened and merged |
| `prs_open` | pull requests opened and still open |
| `prs_reviewed` | pull requests of others reviewed |
| `prs_total` | pull requests opened, in total |
| `prs_unmerged` | pull requests opened and closed without merging |
| `user_association` | text, always lowercase, ordered by privilege: owner > member > collaborator > contributor > first_timer > first_time_contributor > mannequin > none > empty; the most privileged seen |
| `user_bot` | True if the handle contains [bot] or is Copilot, else False |
| `user_handle` | text: the GitHub login |

The numbers are whole numbers, `days_first`, `days_last` and `days_to_merge` are
infinite if there is no data, `user_bot` is True or False. Comparisons of numbers
are `>=`, `<=`, `==`, `!=`, `>` and `<` (also chained). Text is compared in any
case with `==` and `!=`, and `in` and `not in` tell whether the text on the left
is part of the one on the right: `"[bot]" in user_handle`, or
`user_association in "owner member"` (an empty association is part of any
text). `user_association` is ordered by privilege: `owner` > `member` >
`collaborator` > `contributor` > `first_timer` > `first_time_contributor` >
`mannequin` > `none` > unknown, so `user_association >= association_member` and
`user_association < "contributor"` work. The names are written as text or with
the prefix `association_` (`association_owner`, `association_member`, ...,
`association_none`). An unknown
name is reported with the closest ones ("Did you mean ...?") and all the names,
sorted. Combine with `and`, `or`, `not` and parentheses; `not` binds tightest,
then `and`, then `or`. There are no functions.

### Configuration

```sh
gh-community config create                # asks for token and repositories
gh-community config token set|show|delete     # show masks the token; --reveal prints it
gh-community config repo add|list|delete owner/name   # delete and contributors also accept a short name
```

Token precedence: `--token` (accepted by every command that uses the API), `$GITHUB_TOKEN` (as
provided in GitHub Actions), then `token:` in the config.
The config is read from `--config`, `./config.yaml` or
`$XDG_CONFIG_HOME/gh-community/config.yaml` (default `~/.config/...`), which is also where `config create` writes.

## License

GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).
