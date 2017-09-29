from typing import List, Tuple, Union

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from git import Commit as GitCommit, Repo, TagReference
from sphinx.application import Sphinx
from sphinx.config import Config

from .models import (
    Commit,
    Tag,
    Unreleased,
)

GROUP_HEADINGS = dict(
    build = 'Build System Changes',
    chore = 'Chores',
    ci = 'Change related to CI',
    docs = 'Changes to Documentation',
    feat = 'New Features',
    fix = 'Bug Fixes',
    perf = 'Performance Enhancements',
    refactor = 'Code Refactor',
    style = 'Code Style Changes',
    test = 'Testing Changes',
)


def format_groups(value: str):
    return list(map(lambda x: x.strip(), value.split()))


class GitChangelog(Directive):
    has_content = True
    option_spec = dict(
        # groups = lambda x: x.split(',') if x is not None else None,
        groups = format_groups,
        unreleased = directives.flag,
    )
    optional_arguments = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo = Repo()
        self._current_id = 0

    # noinspection PyArgumentList
    def run(self):
        repo = Repo()
        items = list()
        releases, unreleased = self._walk_commits()

        config: Config = self.state.document.settings.env.app.config
        included_groups = self.options.get('groups', ('feat', 'fix'))

        issues_url = config.git_changelog_issues_url
        releases_url = config.git_changelog_releases_url
        if releases_url is not None:
            git_url = '/'.join(releases_url.split('/')[:-2])
        else:
            git_url = None

        if 'unreleased' in self.options and len(unreleased.commits) > 0:
            unreleased_sec = nodes.section(ids = [unreleased.name.lower()])
            unreleased_sec_title = nodes.title(text = str())
            unreleased_sec.append(unreleased_sec_title)

            unreleased_sec_title.append(nodes.reference(
                rawtext = unreleased.name,
                text = unreleased.name,
                refuri = git_url + f'/tree/{repo.active_branch}' if git_url is not None else '#',
            ))

            items.append(unreleased_sec)

            for group, commits in unreleased.groups.items():
                if group not in included_groups:
                    continue

                group_section = nodes.section(ids = [group.lower()])

                if group in GROUP_HEADINGS:
                    group_title = GROUP_HEADINGS[group]
                else:
                    group_title = group.title()

                group_section.append(nodes.title(text = group_title))
                unreleased_sec.append(group_section)

                commits_list = nodes.bullet_list(classes = [
                    'changelog',
                    'commits-list',
                ])
                group_section.append(commits_list)

                for commit in commits:
                    list_item = nodes.list_item(classes = [
                        'changelog',
                        'commits-list',
                        'commits-list-item',
                    ])
                    commits_list.append(list_item)

                    header = nodes.paragraph(
                        text = f'{commit.summary}'
                               f' {"[" + commit.scope + "]" if commit.scope is not None else str()}'
                    )
                    list_item.append(header)

                    if commit.body is not None:
                        commit_body_list = nodes.bullet_list(classes = [
                            'changelog',
                            'commits-list',
                            'commits-list-item',
                            'commits-list-item-body',
                        ])
                        list_item.append(commit_body_list)
                        commit_body_item = nodes.list_item(classes = [
                            'changelog',
                            'commits-list',
                            'commits-list-item',
                            'commits-list-item-body-item'
                        ])
                        commit_body_list.append(commit_body_item)

                        commit_body_item.append(nodes.paragraph(commit.body, commit.body))

        for release in releases:
            release_section = nodes.section(ids = [release.name.lower()])
            items.append(release_section)

            release_section_title = nodes.title(text = '')
            release_section.append(release_section_title)

            release_section_title.append(nodes.reference(
                text = release.name,
                rawtext = release.name,
                refuri = releases_url.format(release.name) if releases_url is not None else '#',
                classes = [
                    'changelog',
                    'release',
                    'release-title',
                    'release-title-version',
                ]
            ))

            release_section.append(nodes.raw(
                text = f'<h4>Released: <span style="font-size: 80%"> {release.date.date()}</span></h4>',
                rawtext = f'Released: {release.date.date()}',
                format = 'html',
                classes = [
                    'changelog',
                    'release',
                    'release-title',
                    'release-title-date',
                ]
            ))

            commits_list = nodes.bullet_list()
            release_section.append(commits_list)

            for group, commits in release.groups.items():
                if group not in included_groups:
                    continue

                group_section = nodes.section(ids = [group.lower()])

                if group in GROUP_HEADINGS:
                    group_title = GROUP_HEADINGS[group]
                else:
                    group_title = group.title()

                group_section.append(nodes.title(text = group_title))
                release_section.append(group_section)

                commits_list = nodes.bullet_list()
                group_section.append(commits_list)

                for commit in commits:
                    list_item = nodes.list_item()
                    commits_list.append(list_item)

                    header = nodes.paragraph(text = commit.summary)
                    list_item.append(header)

                    if commit.body is not None:
                        header.append(nodes.comment(text = commit.body))

        return items

    def _render_commits(self, commits, node):
        pass

    def _walk_commits(self) -> Tuple[List[Tag], Union[Unreleased, None]]:
        tags: List[TagReference] = self.repo.tags
        if len(tags) < 1:
            raise ValueError('Cannot generate changelog from repo with '
                             'no tags.')

        wrapped_tags = list()

        for tagref in tags:
            tag = Tag(
                name = tagref.name,
                date = tagref.commit.committed_date,
                commit = tagref.commit
            )

            wrapped_tags.append(tag)

        commits = list(map(Commit, self.repo.iter_commits()))

        untagged = self._group_commits(wrapped_tags, commits)

        if untagged is not None:
            unreleased = Unreleased(untagged)
        else:
            unreleased = None

        return wrapped_tags, unreleased

    @staticmethod
    def _group_commits(tags: List[Tag], commits: List[GitCommit]):
        tags = sorted(tags, key = lambda t: t.date)
        commits.extend([Commit(t.commit) for t in tags])

        commits = list(filter(lambda c: c.category,
                              sorted(commits, key = lambda c: c.date)))

        for index, tag in enumerate(tags):
            if index == 0:
                children = list(filter(lambda c: c.date <= tag.date, commits))
            else:
                prev_tag = tags[index - 1]
                children = list(filter(lambda c: prev_tag.date < c.date <= tag.date, commits))

            for child in children:
                commits.remove(child)
                tag.add_commit(child)

        unreleased = list(filter(lambda c: c.date > tags[-1].date, commits))

        return unreleased


def setup(app: Sphinx):
    app.add_config_value('git_changelog_releases_url', None, True)
    app.add_config_value('git_changelog_issues_url', None, True)

    app.add_directive('gitchangelog', GitChangelog)
