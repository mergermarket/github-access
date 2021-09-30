import os
from github import Github



class App:
    def __init__(self, org_name, github_token):

        self.github_token = github_token

        self.github = Github(github_token)
        self.org = self.github.get_organization(org_name)
        self.teams = {
            team.name: team
            for team
            in self.org.get_teams()
        }

github_token = os.environ['GITHUB_TOKEN']
app = App('mergermarket', github_token)
print(app.teams.get('DevTeam-System'))