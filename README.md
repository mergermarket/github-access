This container can be used to set the repository permissions for a team.

Usage:

    export GITHUB_TOKEN=my-team-member-github-token
    docker run -i -w $PWD -v $PWD -e GITHUB_TOKEN mergermark/github-access \\
        --org my-org \\
        --team my-team \\
        --access access.json

access.json should be a json file containing desired permissions for each of
the repositories that `my-team` has access to - for example:

    {
      "my-repo": {
        "teams": {
          "a-github-team-to-give-admin-access-to": "admin",
          "a-github-team-to-give-push-access-to": "push",
          "a-github-team-to-give-pull-access-to": "pull",
        }
      }
    }

Errors will be produced if access.json contains repos that you don't have admin
access to, or if you have admin access to repos not in access.json. Otherwise
it will enforce that the team access to the listed repositories is as
specified in the file. You can start with an empty file to find out what repos
you have admin access to.
