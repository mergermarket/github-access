import json
import os
import argparse
import sys


from github import Github


def main():
    argument_parser = argparse.ArgumentParser('github_access')
    argument_parser.add_argument('--org_name', required=True)
    argument_parser.add_argument('--team_slug', required=True)

    arguments = argument_parser.parse_args(sys.argv[1:])

    github_token = os.environ['GITHUB_TOKEN']
    github = Github(github_token)
    org = github.get_organization(arguments.org_name)

    team = org.get_team_by_slug(arguments.team_slug)

    with open('access.json', 'r') as f:
        access_config = json.loads(f.read())
        for level in access_config:
            for repo_name in level['repos']:
                repo = org.get_repo(repo_name)
                rtn_val = team.update_team_repository(repo, "admin")
                print(repo)


main()     
