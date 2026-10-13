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
gh-community contributors all --sort commits
gh-community contributors all owner/name other/repo --token ...  # overrides the config
```

Output is a Markdown table with right-aligned numbers:

| Column | Meaning |
| ------ | ------- |
| `handle` | GitHub login |
| `commits` | commits in the contributors list |
| `prs` | `merged/total` pull requests opened |
| `issues opened` | issues opened (pull requests are not issues) |
| `issues commented on` | distinct issues with a comment by the user |
| `PRs commented on` | distinct pull requests opened by someone else with a comment by the user (comments and comments on the changes) |
| `PRs reviewed` | distinct pull requests opened by someone else with a submitted review by the user |
| `last activity` | days ago of the newest activity in the repositories: any of the data read: a commit, pull request, issue, comment, review, commit comment or an action on an issue or pull request such as closing, merging or labelling |

The number of comments does not matter, only on how many issues or pull requests
there is one. `--sort` takes `handle`, `commits`, `prs` (the default, by merged
pull requests only), `opened`, `commented`, `pr_commented`, `reviewed` or
`activity` (newest first).

Progress and the API calls used are printed to stderr. Responses are cached in
`$TMPDIR/gh-community-cache-<uid>` using ETags: repeating an analysis only
downloads what changed, and requests answered with `304 Not Modified` do not
count against the rate limit. The first analysis of a repository needs one
request per contributor (latest commit) and one per pull request (reviews).
Reviews and latest commits are not even requested again while the pull request's
`updated_at` or the contributor's number of commits is the same.
`--no-cache` skips the cache, `--cache-dir` moves it. Pages and the per-contributor and
per-pull-request requests are sent in parallel (`--jobs`, default 4).

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
