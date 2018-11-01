import argparse
import sys
import os
import json
import logging
import requests

from github import Github
from . dependabot import DependabotRepo


class App:
    def __init__(self, org_name, main_team_name, github_token, on_error):
        self.on_error = on_error
        # Need the github token to call /user/installations
        # as PyGithub does not implement it.
        # Check https://github.com/PyGithub/PyGithub/issues/828 for latest
        self.github_token = github_token

        self.github = Github(github_token)
        self.org = self.github.get_organization(org_name)
        self.teams = {
            team.name: team
            for team
            in self.org.get_teams()
        }
        self.main_team = self.teams[main_team_name]

    def run(self, access_config):
        seen = set()
        for repo in self.main_team.get_repos():
            if repo.archived or not repo.permissions.admin:
                continue
            seen.add(repo.name)
            self.handle_repo(repo, access_config.get(repo.name))
        self.check_unknown_repos(access_config, seen)

    def handle_repo(self, repo, repo_access_config):
        if repo_access_config is None:
            self.on_error(
                f'team has admin access to {repo.name}, but there is no config'
                ' for that repository'
            )
            return
        self.enforce_repo_access(repo, repo_access_config['teams'])
        self.enforce_app_access(repo, repo_access_config['apps'])

    def check_unknown_repos(self, access_config, seen):
        for name in access_config:
            if name not in seen:
                self.on_error(
                    f'config contained repo {name}, but team does not have '
                    'admin access'
                )

    def _add_repo_to_app(self, app_name, repo):
        apps = {
            'dependabot': '185591',
            'slack': '176550'
        }
        url = (
            f"https://api.github.com"
            f"/user/installations/{apps.get(app_name)}/repositories/{repo.id}"
        )
        headers = {
            'Authorization': f"token {self.github_token}",
            'Accept': "application/vnd.github.machine-man-preview+json",
            'Cache-Control': "no-cache",
        }
        response = requests.request("PUT", url, headers=headers)
        if response.status_code != 204:
            error_message = (
                f"Failed to add repo {repo.name}"
                f" to {app_name} app installation"
            )
            self.on_error(error_message)

    def enforce_app_access(self, repo, desired_permission_by_app):
        for app_name, value in desired_permission_by_app.items():
            self._add_repo_to_app(app_name, repo)
            if app_name == 'dependabot':
                DependabotRepo(repo, self.on_error, self.github_token).add_configs_to_dependabot()


    def enforce_repo_access(self, repo, desired_permission_by_team):
        teams = repo.get_teams()
        if not self.main_team_has_admin_access_to_repo(teams):
            self.on_error(
                f'team does not have admin access to repo {repo.name}'
            )
            return
        current_permission_by_team = {
            team.name: team.permission for team in teams
            if team.name != self.main_team.name
        }
        all_teams = set(
            list(desired_permission_by_team) +
            list(current_permission_by_team)
        )
        for team_name in all_teams:
            team = self.teams.get(team_name)
            if team is None:
                self.on_error(
                    f'unknown team {team_name} specified for repo {repo.name}'
                )
                continue
            self.update_team_permission(
                team, repo, current_permission_by_team.get(team_name),
                desired_permission_by_team.get(team_name)
            )

    def update_team_permission(
        self, team, repo, current_permission, desired_permission
    ):
        if desired_permission == 'admin':
            self.on_error(
                f'additional team {team.name} has admin access to'
                f' repo {repo.name} (resolve by completing transfer)'
            )
        if current_permission == desired_permission:
            logging.info(
                f'team {team.name} {desired_permission} permission to repo '
                f'{repo.name} unchanged'
            )
            return
        if desired_permission is None:
            logging.info(
                f'revoking team {team.name} {current_permission} permission '
                f'from repo {repo.name} '
            )
            team.remove_from_repos(repo)
        else:
            logging.info(
                f'granting team {team.name} {desired_permission} permission '
                f'to repo {repo.name} (was {current_permission})'
            )
            team.set_repo_permission(repo, desired_permission)

    def main_team_has_admin_access_to_repo(self, teams):
        main_team_access = [
            team for team in teams if team.name == self.main_team.name
        ]
        assert len(main_team_access) <= 1
        return len(main_team_access) == 1  \
            and main_team_access[0].permission == 'admin'


def validate_main_team_not_configured(teams, main_team):
    for team in teams:
        if team == main_team:
            raise Exception(
                f'team {team} should not be listed - this is implied'
            )


def validate_access_config(access_config, main_team):
    seen = set()
    for level in access_config:
        validate_main_team_not_configured(level['teams'], main_team)
        for repo in level['repos']:
            if repo in seen:
                raise Exception(f'repo {repo} listed twice')
            seen.add(repo)


def convert_access_config(access_config, main_team):
    validate_access_config(access_config, main_team)
    return {
        repo: {'teams': level['teams'], 'apps': level.get('apps', {})}
        for level in access_config
        for repo in level['repos']
    }


def repo_access(args, handle_error):
    argument_parser = argparse.ArgumentParser('github_access')
    argument_parser.add_argument('--org', required=True)
    argument_parser.add_argument('--team', required=True)
    argument_parser.add_argument('--access', required=True)

    arguments = argument_parser.parse_args(args)

    github_token = os.environ['GITHUB_TOKEN']
    app = App(arguments.org, arguments.team, github_token, handle_error)

    with open(arguments.access, 'r') as f:
        app.run(
            convert_access_config(
                json.loads(f.read()),
                arguments.team
            )
        )

