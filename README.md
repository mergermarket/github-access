# Github Access

This container can be used to set the repository permissions for a team.

Usage:

    export GITHUB_TOKEN=my-team-member-github-token
    docker run -i -w $PWD -v $PWD -e GITHUB_TOKEN mergermark/github-access \
        --org my-org \
        --team my-team \
        --access access.json

access.json should be a json file containing desired permissions for each of
the repositories that `my-team` has access to - for example:

    [
      {
        "teams": {
          "a-github-team-to-give-admin-access-to": "admin",
          "a-github-team-to-give-push-access-to": "push",
          "a-github-team-to-give-pull-access-to": "pull",
        },
        "repos": [ "repo1", "repo2" ]
      }
    ]

The following equivalent format is also supported, but should be considered
deprecated since it causes duplication:

    {
      "repo1": {
        "teams": {
          "a-github-team-to-give-admin-access-to": "admin",
          "a-github-team-to-give-push-access-to": "push",
          "a-github-team-to-give-pull-access-to": "pull",
        }
      },
      "repo2": {
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

Note that you do not have to (and should not) included `my-team` in the repo
permissions - this team's admin permission will be left alone. To transfer
admin to another team, add admin privilege to that team (during transfer this
will result in an ignorable error). Now that they have admin, they will be able
revoke the original team's admin access - at this point the error will change
and the repository should be removed from the file.

## Github Apps

When you want to add Github Apps to your repo you should specify a json mapping
of slack app names to ids and pass it into the docker run command with the 
`--apps` flag.

Example:
```
export GITHUB_TOKEN=my-team-member-github-token
docker run -i -w $PWD -v $PWD -e GITHUB_TOKEN mergermark/github-access \
    --org my-org \
    --team my-team \
    --access access.json
    --apps $(cat apps.json)
```

The json being in the format:
```
{
    "slack": "123456",
    "jira": "888888"
}
```
