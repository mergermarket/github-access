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

    def run(self, access_config):
        seen = set()
        for repo in self.main_team.get_repos():
            if repo.archived:
                continue
            seen.add(repo.name)
            self.handle_repo(repo, access_config.get(repo.name))
        self.check_unknown_repos(access_config, seen)

    def handle_repo(self, repo, repo_access_config):
        if not repo.permissions.admin:
            return
        if repo_access_config is None:
            self.on_error(
                f'team has admin access to {repo.name}, but there is no config'
                ' for that repository'
            )
            return
        self.enforce_repo_access(repo, repo_access_config['teams'])

    def check_unknown_repos(self, access_config, seen):
        for name in access_config:
            if name not in seen:
                self.on_error(
                    f'config contained repo {name}, but no info about this '
                    'repo was returned from Github'
                )

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
        repo: {'teams': level['teams']}
        for level in access_config
        for repo in level['repos']
    }


def main(args, github_token):

    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser('github_access')
    argument_parser.add_argument('--org', required=True)
    argument_parser.add_argument('--team', required=True)
    argument_parser.add_argument('--access', required=True)

    arguments = argument_parser.parse_args(args)

    failed = False

    def handle_error(err):
        nonlocal failed
        logging.error(err)
        failed = True

    app = App(arguments.org, arguments.team, github_token, handle_error)

    with open(arguments.access, 'r') as f:
        app.run(
            convert_access_config(
                json.loads(f.read()),
                arguments.team
            )
        )

    if failed:
        print('error(s) were encountered - see above', file=sys.stderr)
        sys.exit(1)
