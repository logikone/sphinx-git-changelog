import re
from collections import defaultdict
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Tuple

from git import Commit as GitCommit

CommitGroups = Dict[str, List['Commit']]


class Commit(object):
    __slots__ = (
        'body',
        'category',
        'commit',
        'date',
        'footer',
        'hash',
        'header',
        'message',
        'scope',
        'summary',
        'tag',
    )

    def __init__(self, commit: GitCommit):
        self.commit = commit
        self.date = datetime.fromtimestamp(commit.committed_date)
        self.hash = commit.hexsha
        self.message = commit.message
        self.tag = None

        self.header, self.body, self.footer = self.split_message()
        self.category, self.scope, self.summary = self.categorize()

    def categorize(self):
        match = re.match(r'(\w+)(\(.+\))?:\s*(.*)', self.header)

        if match:
            category, scope, description = match.groups()

            if scope is not None:
                scope = scope[1:-1]

            result = category, scope, description
        else:
            result = None, None, None

        return result

    def split_message(self) -> Tuple[str, List[str], List[str]]:
        sections = self.message.split('\n\n')
        header = sections.pop(0)
        footer = None

        if len(sections) > 1:
            footer = sections.pop().splitlines()
            body = '\n'.join(sections).splitlines()
        elif len(sections) == 0:
            body = None
        else:
            body = sections.pop()

        assert len(sections) == 0

        return header, body, footer


class Tag(object):
    __slots__ = (
        'commit',
        'commits',
        'date',
        'groups',
        'name',

    )

    def __init__(self,
                 name: str,
                 date: int,
                 commit: GitCommit):
        self.commit = commit
        self.commits = list()
        self.date = datetime.fromtimestamp(date)
        self.groups: CommitGroups = defaultdict(list)
        self.name = name

    def add_commit(self, commit: Commit):
        commit.tag = self
        self.commits.append(commit)
        self.groups[commit.category].append(commit)


class Unreleased(object):
    __slots__ = (
        'commits',
        'groups',
        'name',
    )

    def __init__(self, commits: List[Commit]):
        self.commits = commits
        self.groups: CommitGroups = defaultdict(list)
        self.name = 'Unreleased'

        for commit in commits:
            self.add_commit(commit)

    def add_commit(self, commit: Commit):
        self.groups[commit.category].append(commit)
