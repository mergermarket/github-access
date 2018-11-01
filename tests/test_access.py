import unittest
from unittest.mock import Mock, patch, mock_open, ANY
import json

import github_access


class TestArgs(unittest.TestCase):

    @patch('github_access.github.App')
    def test_args(self, App):

        # given
        access = [{'repos': ['test'], 'teams': {}}]
        with patch(
            'github_access.github.open',
            mock_open(read_data=json.dumps(access)),
            create=True
        ) as mocked_open:
            with patch.dict(
                'github_access.github.os.environ',
                {'GITHUB_TOKEN': 'test-github-token'}
            ):
                # when
                github_access.github.repo_access([
                    '--org', 'test-org',
                    '--team', 'test-team',
                    '--access', 'test-file.json'
                ], 'test-github-token')

            # then
            App.assert_called_once_with(
                'test-org', 'test-team', 'test-github-token', ANY
            )
            mocked_open.assert_called_once_with('test-file.json', 'r')
            App.return_value.run.assert_called_once_with({
                'test': {'teams': {}, 'apps': {}}
            })


class TestFormatConversion(unittest.TestCase):

    def test_array_conversion(self):

        self.assertEqual(
            github_access.github.convert_access_config([
                {
                    'teams': {'team-a': 'pull', 'team-b': 'push'},
                    'repos': ['repo-a', 'repo-b']
                },
                {
                    'teams': {'team-c': 'pull'},
                    'repos': ['repo-c']
                }
            ], 'test-main-team'),
            {
                'repo-a': {
                    'teams': {'team-a': 'pull', 'team-b': 'push'},
                    'apps': {}
                },
                'repo-b': {
                    'teams': {'team-a': 'pull', 'team-b': 'push'},
                    'apps': {}
                },
                'repo-c': {
                    'teams': {'team-c': 'pull'},
                    'apps': {}
                }
            }
        )


class TestApp(unittest.TestCase):

    @patch('github_access.github.Github')
    def setUp(self, Github):

        org_name = 'test-org'
        self.github_token = 'test-github-token'

        self.main_team = Mock()
        self.main_team.name = 'test-team'

        self.test_admin_team = Mock()
        self.test_admin_team.name = 'test-admin-team'
        self.test_push_team = Mock()
        self.test_push_team.name = 'test-push-team'
        self.test_pull_team = Mock()
        self.test_push_team.name = 'test-pull-team'

        github = Github.return_value

        self.org = github.get_organization.return_value
        self.org.get_teams.return_value = [
            self.main_team, self.test_admin_team, self.test_push_team,
            self.test_pull_team
        ]
        self.errors = []

        def handle_error(err):
            self.errors.append(err)

        self.app = github_access.github.App(
            org_name, self.main_team.name, self.github_token, handle_error
        )
        Github.assert_called_once_with(self.github_token)
        github.get_organization.assert_called_once_with(org_name)
        self.org.get_teams.assert_called_once_with()

    def test_additional_team_permissions(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        repo.get_teams.return_value = [main_team_repo_access]

        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({
            repo_name: {
                'teams': {
                    self.test_admin_team.name: 'admin',
                    self.test_push_team.name: 'push',
                    self.test_pull_team.name: 'pull'
                },
                'apps': {}
            }
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_called_once_with()
        self.test_admin_team.set_repo_permission.called_once_with(
            repo, 'admin'
        )
        self.test_push_team.set_repo_permission.called_once_with(repo, 'push')
        self.test_pull_team.set_repo_permission.called_once_with(repo, 'pull')
        assert self.errors == [
            f'additional team {self.test_admin_team.name} has admin access to'
            f' repo {repo_name} (resolve by completing transfer)'
        ]

    def test_team_permissions_modified(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        admin_team_repo_access = Mock()
        admin_team_repo_access.name = self.test_admin_team.name
        admin_team_repo_access.permission = 'admin'

        push_team_repo_access = Mock()
        push_team_repo_access.name = self.test_push_team.name
        push_team_repo_access.permission = 'push'

        pull_team_repo_access = Mock()
        pull_team_repo_access.name = self.test_pull_team.name
        pull_team_repo_access.permission = 'pull'

        repo.get_teams.return_value = [
            main_team_repo_access, admin_team_repo_access,
            push_team_repo_access, pull_team_repo_access
        ]

        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({
            repo_name: {
                'teams': {
                    self.test_admin_team.name: 'push',
                    self.test_push_team.name: 'pull',
                    self.test_pull_team.name: 'admin'
                },
                'apps': {}
            }
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_called_once_with()
        self.test_admin_team.set_repo_permission.called_once_with(repo, 'push')
        self.test_push_team.set_repo_permission.called_once_with(repo, 'pull')
        self.test_pull_team.set_repo_permission.called_once_with(repo, 'admin')
        assert self.errors == [
            f'additional team {self.test_pull_team.name} has admin access to'
            f' repo {repo_name} (resolve by completing transfer)'
        ]

    def test_team_permissions_removed(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        admin_team_repo_access = Mock()
        admin_team_repo_access.name = self.test_admin_team.name
        admin_team_repo_access.permission = 'admin'

        push_team_repo_access = Mock()
        push_team_repo_access.name = self.test_push_team.name
        push_team_repo_access.permission = 'push'

        pull_team_repo_access = Mock()
        pull_team_repo_access.name = self.test_pull_team.name
        pull_team_repo_access.permission = 'pull'

        repo.get_teams.return_value = [
            main_team_repo_access, admin_team_repo_access,
            push_team_repo_access, pull_team_repo_access
        ]

        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({
            repo_name: {
                'teams': {},
                'apps': {}
            }
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_called_once_with()
        self.test_admin_team.remove_from_repos.called_once_with(repo)
        self.test_push_team.remove_from_repos.called_once_with(repo)
        self.test_pull_team.remove_from_repos.called_once_with(repo)

    def test_repo_not_configured_error(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        repo.get_teams.return_value = [main_team_repo_access]

        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({})

        # then
        assert self.errors == [
            f'team has admin access to {repo.name}, but there is no config'
            ' for that repository'
        ]

    def test_pull_repo_ignored(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = False
        repo.permissions.push = False
        repo.permissions.pull = True
        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({})

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_not_called()

    def test_push_repo_ignored(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = False
        repo.permissions.push = True
        repo.permissions.pull = True
        self.main_team.get_repos.return_value = [repo]

        # when
        self.app.run({})

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_not_called()

    def test_repo_admin_for_another_team_ignored(self):
        '''
        This should not come up in normal operation since it will be run by a
        system user that is only a member of one team, but it may be run by a
        user who is a member of other teams than one passed on the command
        line, so there could be repos that the user has admin to that the team
        doesn't.
        '''

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True
        self.main_team.get_repos.return_value = [repo]

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'push'

        repo.get_teams.return_value = [main_team_repo_access]

        # when
        self.app.run({
            repo_name: {'teams': {}, 'apps': {}}
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_called_once_with()
        assert self.errors == [
            f'team does not have admin access to repo {repo_name}'
        ]

    def test_unknown_team_error(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True
        self.main_team.get_repos.return_value = [repo]

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        repo.get_teams.return_value = [main_team_repo_access]

        # when
        self.app.run({
            repo_name: {
                'teams': {
                    'not-a-team': 'push'
                },
                'apps': {}
            }
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        repo.get_teams.assert_called_once_with()
        assert self.errors == [
            f'unknown team not-a-team specified for repo {repo_name}'
        ]

    def test_error_on_unknown_repo(self):

        # given
        self.main_team.get_repos.return_value = []

        # when
        self.app.run({
            'unknown-repo': {}
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        assert self.errors == [
            f'config contained repo unknown-repo, but team does not have '
            'admin access'
        ]

    def test_error_on_unknown_repo_with_write(self):

        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = False
        self.main_team.get_repos.return_value = [repo]

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'write'

        repo.get_teams.return_value = [main_team_repo_access]

        # when
        self.app.run({
            repo_name: {}
        })

        # then
        self.main_team.get_repos.assert_called_once_with()
        assert self.errors == [
            f'config contained repo {repo_name}, but team does not have '
            'admin access'
        ]

    @patch('github_access.github.DependabotRepo')
    def test_adding_dependabot(self, mock_dependabot):
        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True
        repo.id = '1234567890'

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        repo.get_teams.return_value = [
            main_team_repo_access
        ]

        self.main_team.get_repos.return_value = [repo]

        url = (
            f"https://api.github.com"
            f"/user/installations/185591/repositories/{repo.id}"
        )
        headers = {
            'Authorization': f"token {self.github_token}",
            'Accept': "application/vnd.github.machine-man-preview+json",
            'Cache-Control': "no-cache",
        }

        mock_dependabot.add_configs_to_dependabot.return_value = True
        # when
        with patch('github_access.github.requests') as requests:
            self.app.run({
                repo_name: {
                    'teams': {
                        self.main_team.name: 'admin'
                    },
                    'apps': {
                        'dependabot': 'true'
                    }
                }
            })
            requests.request.return_value.status_code = 200
            requests.request.assert_called_once_with("PUT", url, headers=headers)

    def test_adding_slack(self):
        # given
        repo_name = 'test-repo'

        repo = Mock()
        repo.archived = False
        repo.name = repo_name
        repo.permissions.admin = True
        repo.id = '1234567890'

        main_team_repo_access = Mock()
        main_team_repo_access.name = self.main_team.name
        main_team_repo_access.permission = 'admin'

        repo.get_teams.return_value = [
            main_team_repo_access
        ]

        self.main_team.get_repos.return_value = [repo]

        url = (
            f"https://api.github.com"
            f"/user/installations/176550/repositories/{repo.id}"
        )
        headers = {
            'Authorization': f"token {self.github_token}",
            'Accept': "application/vnd.github.machine-man-preview+json",
            'Cache-Control': "no-cache",
        }

        # when
        with patch('github_access.github.requests') as requests:
            self.app.run({
                repo_name: {
                    'teams': {
                        self.main_team.name: 'admin'
                    },
                    'apps': {
                        'slack': 'true'
                    }
                }
            })
            requests.request.return_value.status_code = 200
            requests.request.assert_called_once_with("PUT", url, headers=headers)
