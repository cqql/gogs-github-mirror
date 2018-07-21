#!/usr/bin/env python

import argparse
import requests

REPOS_URL = "https://api.github.com/user/repos"


def next_link(response):
    if "Link" not in response.headers:
        return None

    links = requests.utils.parse_header_links(response.headers["Link"])

    next = [link for link in links if link["rel"] == "next"]

    if len(next) > 0:
        return next[0]["url"]
    else:
        return None


def fetch_repos(user, password):
    repos = []
    next_url = REPOS_URL
    while True:
        response = requests.get(next_url, auth=(user, password))
        repos = repos + response.json()

        next_url = next_link(response)

        if not next_url:
            return repos


class Gogs:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password

    def user_id(self):
        url = "{}/api/v1/user".format(self.base_url)
        response = requests.get(url, auth=(self.user, self.password))
        return response.json()["id"]

    def mirror(self, owner_id, repo):
        url = "{}/api/v1/repos/migrate".format(self.base_url)
        body = {
            "clone_addr": repo["clone_url"],
            "uid": owner_id,
            "repo_name": repo["name"],
            "mirror": True,
            "private": repo["private"],
            "description": repo["description"]
        }

        return requests.post(url, json=body, auth=(self.user, self.password))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gh-user", required=True, help="github user")
    parser.add_argument("--gh-pass", help="github password")
    parser.add_argument("--gogs-url", required=True, help="gogs server URL")
    parser.add_argument("--gogs-user", required=True, help="gogs user")
    parser.add_argument("--gogs-pass", help="gogs password")
    parser.add_argument("--with-forks", type=bool, help="Mirror forks")
    args = parser.parse_args()

    gh_user = args.gh_user
    gh_pass = args.gh_pass
    gogs_url = args.gogs_url
    gogs_user = args.gogs_user
    gogs_pass = args.gogs_pass
    with_forks = args.with_forks

    if not gh_pass:
        gh_pass = input("Github password: ")
    if not gogs_pass:
        gogs_pass = input("Gogs password: ")

    # Load repositories
    repos = fetch_repos(gh_user, gh_pass)

    # Filter out repos from orgs that the user belongs to
    repos = [r for r in repos if r["owner"]["login"] == gh_user]

    # Filter out forks
    if not with_forks:
        repos = [r for r in repos if not r["fork"]]

    # Set up the mirrors
    gogs = Gogs(gogs_url, gogs_user, gogs_pass)
    gogs_id = gogs.user_id()
    for repo in repos:
        response = gogs.mirror(gogs_id, repo)
        if response.status_code == 201:
            print("Mirror for {} set up".format(repo["name"]))
        elif response.status_code == 500:
            print("Repository {} already exists".format(repo["name"]))
        else:
            print("Unknown error {} for repo {}".format(response.status_code, repo["name"]))


if __name__ == "__main__":
    main()
