#!/usr/bin/env python

# SIRI: Should I Rewrite It?
#
# This script requires gitpython to run. Install gitpython into your
# Python environment using:
#
#  pip install gitpython
#
# This may require elevated privileges through sudo.

import argparse
import json
import os

try:
    import git
except ImportError:
    print("Install gitpython before running this script.\npip install gitpython")
    exit()


siri_authors = {}
code_files = []
resource_files = []

with open("siri.config.json") as json_data:
    config = json.load(json_data)
    siri_authors = config["authors"]
    code_files = config["code-files"]
    resource_files = config["resource-files"]

class AuthorStats:
    def __init__(self):
        self.blank_lines = 0
        self.comments = 0
        self.commits = set()
        self.lines = 0

    def add_commit(self, commit):
        self.commits.add(commit.hexsha)

    def add_lines(self, lines):
        for line in lines:
            line = line.strip()
            if len(line) == 0:
                self.blank_lines += 1
            elif line.startswith("//"):
                self.comments += 1
            else:
                self.lines += 1

    def merge(self, stats):
        self.blank_lines += stats.blank_lines
        self.comments += stats.comments
        self.commits = self.commits.union(stats.commits)
        self.lines += stats.lines


class FileStats:
    def __init__(self):
        self.authors = {}

    def add_author(self, email):
        if email not in self.authors:
            self.authors[email] = AuthorStats()
        return self.authors[email]

    def add_blame(self, commit, lines):
        email = commit.author.email
        author = self.add_author(email)
        author.add_commit(commit)
        author.add_lines(lines)

    def aggregate(self):
        aggr = AuthorStats()
        for _, stats in self.authors.items():
            aggr.merge(stats)
        return aggr

    def authors_by_activity(self):
        def by_activity(a, b):
            return self.authors[a].lines - self.authors[b].lines
        return sorted(self.authors.keys(), by_activity)

    def authors_by_email(self):
        return sorted(self.authors.keys())

    def merge(self, stats):
        for author, author_stats in stats.authors.items():
            a = self.add_author(author)
            a.merge(author_stats)


def analyze_file(repo, filename):
    stats = FileStats()
    for commit, lines in repo.blame("HEAD", filename):
        stats.add_blame(commit, lines)
    return stats


def get_filenames_from_repo(repo, dir, recursive):
    rsub = repo.head.commit.tree

    if len(dir) > 0:
        for path_component in dir.split(os.path.sep):
            rsub = rsub[path_component]

    files = []
    if recursive:
        for subtree in rsub.trees:
            files.extend(get_filenames_from_repo(repo, subtree.path, True))

    files.extend([x.path for x in rsub.blobs])
    return files


def find_repo(ref_path):
    path = os.path.abspath(ref_path)
    while path != "/":
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        if os.path.isfile(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return None


def print_csv(caption, stats):
    print(caption)

    authors = stats.authors_by_email()
    for author in authors:
        author_stats = stats.authors[author]
        print("{},{},{},{},{}".format(author, author_stats.blank_lines, author_stats.comments, len(author_stats.commits), author_stats.lines))
    print("")


def print_stats(caption, stats):
    print("-" * len(caption))
    print(caption)
    print("-" * len(caption))

    authors = stats.authors_by_activity()
    max_len = reduce(lambda x, y: max(x, len(y)), authors, 0)
    format = "{{:>{}}} - {{}} ({{}})".format(max_len)

    aggr = stats.aggregate()
    if aggr.lines == 0:
        print("No lines of code\n")
        return

    siri_lines = 0
    for author in authors:
        author_stats = stats.authors[author]
        activity = "*" * (100 * author_stats.lines / aggr.lines)
        if len(activity) == 0 and author_stats.lines > 0:
            activity = "."
        print(format.format(author, activity, author_stats.lines))
        if author in siri_authors:
            siri_lines += (author_stats.lines * siri_authors[author]["factor"])

    print("SIRI: {:.0f}%\n".format(100.0 * siri_lines / aggr.lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", action="store_true", help="Only analyze code files")
    parser.add_argument("--resource", action="store_true", help="Only analyze resource files")
    parser.add_argument("--csv", action="store_true", help="Output in CSV format")
    parser.add_argument("-r", "--recursive", action="store_true", help="Analyze files in subdirectories")
    parser.add_argument("-v", "--verbose", action="store_true", help="Include less important output")
    parser.add_argument("filename", type=str, nargs="+", help="File to analyze")
    args = parser.parse_args()

    legit_files = []
    if args.code:
        legit_files.extend(code_files)
    if args.resource:
        legit_files.extend(resource_files)

    total_stats = FileStats()
    total_stats_count = 0

    for filename in args.filename:
        single_stats = FileStats()
        single_stats_count = 0

        repo = git.Repo(find_repo(os.path.join(os.path.abspath("."), filename)))
        abs_filename = os.path.abspath(os.path.join(os.path.abspath("."), filename))
        repo_filename = abs_filename[len(repo.working_tree_dir):].strip("/")
        if os.path.isdir(abs_filename):
            siri_files = get_filenames_from_repo(repo, repo_filename, args.recursive)
            print("{} files in {}".format(len(siri_files), repo_filename))
        else:
            siri_files = [repo_filename]

        for siri_file in siri_files:
            ext = ["." + x for x in siri_file.split(".")]
            if legit_files and ext[-1] not in legit_files:
                continue

            stats = analyze_file(repo, siri_file)

            single_stats.merge(stats)
            single_stats_count += 1

            if args.csv:
                print_csv(siri_file, stats)
            else:
                print_stats(siri_file, stats)

        if single_stats_count > 1:
            if args.csv:
                print_csv("Subtotals from {} files".format(single_stats_count), single_stats)
            else:
                print_stats("Subtotals from {} files".format(single_stats_count), single_stats)

        total_stats.merge(single_stats)
        total_stats_count += single_stats_count

    if total_stats_count > 1:
        if args.csv:
            print_csv("Totals from {} files".format(total_stats_count), total_stats)
        else:
            print_stats("Totals from {} files".format(total_stats_count), total_stats)
