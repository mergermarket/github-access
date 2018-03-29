import argparse
import sys
import json
import logging

from github import Github


class App:
    def __init__(self, org_name, main_team_name, github_token, on_error):
        self.on_error = on_error
        self.github = Github(github_token)
        self.org = self.github.get_organization(org_name)
        self.teams = {
            team.name: team
            for team
            in self.org.get_teams()
        }
        self.main_team = self.teams[main_team_name]

    def enforce_access(self, access):
        seen = set()
        for repo in self.main_team.get_repos():
            seen.add(repo.name)
            if repo.permissions.admin:
                desired = access.get(repo.name)
                if desired is None:
                    self.on_error(f'no config for repo {repo.name}')
                    continue
                self.enforce_repo_access(repo, desired['teams'])
        self.check_unknown_repos(access, seen)

    def check_unknown_repos(self, access, seen):
        for name in access:
            if name not in seen:
                self.on_error(f'unknown repo {name}')

    def enforce_repo_access(self, repo, after):
        teams = [team for team in repo.get_teams()]
        if not self.main_team_has_admin_access_to_repo(teams, repo):
            self.on_error(
                f'team does not have admin access to repo {repo.name}'
            )
            return
        before = {
            team.name: team.permission for team in teams
            if team.name != self.main_team.name
        }
        for team_name in set(list(before.keys()) + list(after.keys())):
            team = self.teams.get(team_name)
            if team is None:
                self.on_error(
                    f'unknown team {team_name} specified for repo {repo.name}'
                )
                continue
            self.update_team_permission(
                team, repo, before.get(team_name),
                after.get(team_name)
            )

    def update_team_permission(self, team, repo, before, after):
        if before == after:
            logging.info(
                f'team {team.name} {after} permission to repo {repo.name}'
                f' unchanged'
            )
            return
        if after is None:
            logging.info(
                f'revoking team {team.name} {before} permission from '
                f'repo {repo.name} '
            )
            team.remove_from_repos(repo)
        else:
            logging.info(
                f'granting team {team.name} {after} permission to repo '
                f'{repo.name} (was {before})'
            )
            team.set_repo_permission(repo, after)

    def main_team_has_admin_access_to_repo(self, teams, repo):
        main_team_access = [
            team for team in teams if team.name == self.main_team.name
        ]
        assert len(main_team_access) <= 1
        return len(main_team_access) == 1  \
            and main_team_access[0].permission == 'admin'


def main(args, github_token):

    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser('github_access')
    argument_parser.add_argument('--org', required=True)
    argument_parser.add_argument('--team', required=True)
    argument_parser.add_argument('--access', required=True)

    arguments = argument_parser.parse_args(args)

    failed = False

    def handle_error(err):
        global failed
        logging.error(err)
        failed = True

    app = App(arguments.org, arguments.team, github_token, handle_error)

    with open(arguments.access, 'r') as f:
        app.enforce_access(json.loads(f.read()))

    if failed:
        sys.exit(1)
