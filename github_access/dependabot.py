import logging
import requests
import os
import json


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DependabotRepo:
    def __init__(self, github_repo, on_error):
        self.name = github_repo.name
        self.id = github_repo.id
        self.on_error = on_error

        self.package_managers = {
            "Ruby": "bundler",
            "JavaScript": "npm_and_yarn",
            "Java": "maven",
            "Rust": "cargo",
            "PHP": "composer",
            "Python": "pip",
            "Elixir": "hex",
            "F#": "nuget",
            "V#": "nuget",
            "Visual Basic": "nuget",
            "Docker": "docker"
        }

        self.github_headers = {
            'Authorization': f"token {os.environ['GITHUB_TOKEN']}",
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Cache-Control': 'no-cache',
        }

        self.dependabot_headers = {
            'Authorization': f"Personal {os.environ['GITHUB_TOKEN']}",
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
        }

        response = requests.request(
                'GET',
                f"https://api.github.com/repos/mergermarket/{self.name}/contents",
                headers=self.github_headers)
        self.repo_files = response.json()

    def has(self, filename):
        for content in self.repo_files:
            if content.get('name') == filename:
                return True
        return False

    def config_files_exist_for(self, lang):
        if lang == 'Docker':
            return self.has('Dockerfile')
        if lang == 'Ruby':
            return self.has('Gemfile') or \
                   self.has('gemspec')
        if lang == 'JavaScript':
            return self.has('package.json')
        if lang == 'PHP':
            return self.has('composer.json')
        if lang == 'Python':
            return self.has('requirements.txt') or \
                   self.has('setup.py') or \
                   (self.has('Pipfile') and self.has('Pipfile.lock'))
        if lang == 'Java':
            return self.has('pom.xml') or \
                   self.has('build.gradle')
        if lang == 'Rust':
            return self.has('Cargo.toml')
        if lang == 'Elixir':
            return self.has('mix.exs') and self.has('mix.lock')
        return False

    def get_package_managers(self):
        package_managers = []
        for lang in requests.request(
                'GET',
                f"https://api.github.com/repos/mergermarket/{self.name}/languages",
                headers=self.github_headers).json():
            if lang in self.package_managers.keys() and self.config_files_exist_for(lang):
                package_managers.append(self.package_managers[lang])

        # Docker not returned as a language
        # from Github but is a valid language in Dependabot
        if self.config_files_exist_for('Docker'):
            package_managers.append(self.package_managers['Docker'])

        return set(package_managers)

    def add_configs_to_dependabot(self):
        for package_mngr in self.get_package_managers():
            data = {
                'repo-id': self.id,
                'package-manager': package_mngr,
                'update-schedule': 'daily',
                'directory': '/',
                'account-id': '2012700',
                'account-type': 'org',
            }
            response = requests.request(
                'POST',
                'https://api.dependabot.com/update_configs',
                data=json.dumps(data),
                headers=self.dependabot_headers)

            if response.status_code == 201 and response.reason == 'Created':
                logger.info(f"Config for repo {self.name}:{package_mngr} added to Dependabot")
            elif response.status_code == 400 and "already exists" in response.text:
                logger.info(f"Config for repo {self.name}:{package_mngr} already exists in Dependabot")
            else:
                self.on_error(
                    f"Failed to add repo {self.name}:{package_mngr} to Dependabot app installation "
                    f"(Staus Code: {response.status_code}:{response.text})"
                )
