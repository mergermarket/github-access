import unittest
from unittest.mock import Mock, patch, mock_open, ANY
import json

import github_access


class TestArgs(unittest.TestCase):

    @patch('github_access.App')
    def test_args(self, App):

        # given
        access = {'test': 1}
        with patch(
            'github_access.open',
            mock_open(read_data=json.dumps(access)),
            create=True
        ) as mocked_open:

            # when
            github_access.main([
                '--org', 'test-org',
                '--team', 'test-team',
                '--access', 'test-file.json'
            ], 'test-github-token')

            # then
            App.assert_called_once_with(
                'test-org', 'test-team', 'test-github-token', ANY
            )
            mocked_open.assert_called_once_with('test-file.json', 'r')
            App.return_value.run.assert_called_once_with(access)


class TestApp(unittest.TestCase):

    @patch('github_access.Github')
    def setUp(self, Github):

        org_name = 'test-org'
        github_token = 'test-github-token'

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

        self.app = github_access.App(
            org_name, self.main_team.name, github_token, handle_error
        )
        Github.assert_called_once_with(github_token)
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
                }
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
                }
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
                'teams': {}
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
            f'no config for repo {repo_name}'
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
            repo_name: {'teams': {}}
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
            repo_name: {'teams': {
                'not-a-team': 'push'
            }}
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
        assert self.errors == ['unknown repo unknown-repo']
