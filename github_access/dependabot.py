import logging
import requests
import os
import json


logger = logging.getLogger()
logger.setLevel(logging.INFO)

package_manager = {
    "Ruby": "bundler",
    "JavaScript": "npm_and_yarn",
    "HTML": "npm_and_yarn",
    "CSS": "npm_and_yarn",
    "Java": "maven",
    "Rust": "cargo",
    "PHP": "composer",
    "Python": "pip",
    "Elixir": "hex",
    "F#": "nuget",
    "V#": "nuget",
    "Visual Basic": "nuget",
    "Dockerfile" : "docker"
}

github_headers = {
    'Authorization': f"token {os.environ['GITHUB_TOKEN']}",
    'Accept': 'application/vnd.github.machine-man-preview+json',
    'Cache-Control': 'no-cache',

}

dependabot_headers = {
    'Authorization': f"Personal {os.environ['GITHUB_TOKEN']}",
    'Cache-Control': 'no-cache',
    'Content-Type':  'application/json',
}


def repo_has_dockerfile(repo):
    response = requests.request(
            'GET',
            f"https://api.github.com/repos/mergermarket/{repo.get('name')}/contents",
            headers=github_headers)

    for content in response.json():
        if content.get('name') == 'Dockerfile':
            return True

    return False


def get_repo_package_managers(repo):
    package_managers = []
    for lang in requests.request(
            'GET',
            f"https://api.github.com/repos/mergermarket/{repo.get('name')}/languages",
            headers=github_headers).json():
        if lang in package_manager.keys():
            package_managers.append(package_manager[lang])

    # Dockerfile not returned as a language
    # from Github but is a valid language in Dependabot
    if repo_has_dockerfile(repo):
        package_managers.append(package_manager['Dockerfile'])

    return set(package_managers)


def create_configs_in_dependabot(repos, on_error):
    for repo in repos:
        for package_mngr in get_repo_package_managers(repo):
            data = {
                'repo-id': repo.get('id'),
                'package-manager': package_mngr,
                'update-schedule': 'daily',
                'directory': '/',
                'account-id': '2012700',
                'account-type': 'org',
            }
            response = requests.request(
                'POST',
                'https://api.dependabot.com/update_configs ',
                json=json.dumps(data),
                headers=dependabot_headers)

            if response.status_code == 201 and response.reason == 'Created':
                logger.info(f"Config for repo {repo.get('name')} added to Depemdabot")
            elif response.status_code == 400:
                logger.info(f"Config for repo {repo.get('name')} already exists Depemdabot")
            else:
                on_error(
                    f"Failed to add repo {repo.get('name')} to Dependabot app installation "
                    f"(Staus Code: {response.status_code})"
                )


def get_github_repos_from_install(
        url="https://api.github.com/user/installations/185591/repositories",
        repos=[]):

    response = requests.request("GET", url, headers=github_headers)
    for repo in response.json().get('repositories'):
        repos.append(repo)

    if response.links.get('next'):
        get_github_repos_from_install(response.links['next']['url'], repos)
    return repos


def add_repo(on_error):
    repos = get_github_repos_from_install()
    create_configs_in_dependabot(repos, on_error)

