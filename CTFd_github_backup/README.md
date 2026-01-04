# Github backup
Import challenges from Github to CTFd

## 1. Create the GitHub App on GitHub
From Settings -> Developer Settings -> Github App -> New Github App.

Complete the form with the application details:
- Name of the Github App
- Description
- Homepage URL: URL of the deployed platform (or localhost)
- Setup URL: URL of the application to which the user will be redirected after completing the installation. For example: `http://localhost:4000/admin/plugins/github_backup`
- Uncheck webhooks
- In the permissions section on repositories:
  - Contents -> Read-only
  - Metadata -> Read-only
- Choose that the Github App can only be installed on our Github account.

Once created, you must modify it and create the Private Key. This private key must be downloaded and its content saved in the plugin's `config.py` file.
You must also indicate the application ID and the installation URL of the Github App in the `config.py` file.

**Note:** Write the private key on a single line, replacing each line break in the original format with `\n`.

Example of `config.py`:
```python
config = {
    "GITHUB_APP_ID": 0000000,
    "GITHUB_APP_INSTALLATION_URL": "https://github.com/apps/github-app-name/installations/new",
    "GITHUB_APP_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\nexample\n-----END RSA PRIVATE KEY-----"
}
```

## 2. Install the GitHub App on our GitHub account
From the CTFd application, go to the application's administration panel and select Plugins -> Github backup.

The first step is to click on the “1. Install Github App” button.

You can only have one active installation per Github App.

In the window, you can choose whether to give access permission to all repositories or only to some of them.

After completing the installation, you will be redirected back to the CTFd platform.

The second step is to click on the “2. Link installation” button to save the installation token in the database.

## 3. Import challenges
Once the installation is complete, a list of repositories that the GitHub App has access to will be displayed.

Select the ones you want to save and click the “Save selected repositories” button.

The “Saved Repositories” table will show the repositories that have been saved. It also shows the date of the last import and the “Import” (or ‘Update’ if a first import has already been made from that repository) and “Delete” buttons.
Deleting a repository from the table does not delete the challenges that have been imported from that repository. The challenges will remain as not imported from GitHub.

You can choose what to do with challenges imported from GitHub that have been deleted from the repository when you perform an “Update.” You can keep them (they will remain as not imported from GitHub) or delete them.

To import from several repositories at once, check the checkboxes for the repositories and click the “Import selected repositories” button.

You can download a sample JSON file from the “Download an example” button to see the structure that each challenge should have.

Example of JSON schema:
```json
{
    "challenge": {
        "uuid": "000000000000000",
        "name": "knock, knock, Neo",
        "description": "Wake up. The matrix has you...",
        "attribution": "author",
        "connection_info": "https://link.com",
        "max_attempts": 3,
        "value": 50,
        "category": "web",
        "type": "standard",
        "state": "visibe or hidden",
        "flags": [
            {
                "uuid": "000000000000000",
                "type": "static",
                "content": "flag{answer}",
                "data": "case_insensitive"
            },
            {
                "uuid": "000000000000000",
                "type": "regex",
                "content": "flag{.a*}",
                "data": ""
            }
        ],
        "tags": [
            "tag1",
            "tag2"
        ],
        "hints": [
            {
                "uuid": "000000000000000",
                "title": "Hint 1",
                "type": "standard",
                "content": "Follow the white rabbit...",
                "cost": 10
            },
            {
                "uuid": "000000000000000",
                "title": "Hint 2",
                "type": "?",
                "content": "?",
                "cost": 20
            }
        ]
    }
}

```

**Fields and permitted values**
Required fields are marked with an `*`.

For each challenge:
- uuid *
- name *
- description *
- attribution
- connection_info
- max_attemps
- value *
- category
- type *: standard (dynamic type not implemented yet)
- state *: visible or hidden

Tags must be text strings.

The fields for each flag are:
- uuid *
- type *: static or regex
- content *
- data: case_insensitive or empty (for case sensitive)

The fields for each hint are:
- uuid *
- title *
- type: standard *
- content * 
- cost *


## 4. Export challenges
The last section of the page shows a table with all the challenges on the platform. This includes those that have been imported from the Github App and those that have been created from the platform.
Challenges can be exported individually or in groups. Individually exported challenges are downloaded as JSON files. Group exports download a zip file with one JSON file for each challenge.

For challenges that have not been imported from the Github App, a UUID will be generated in the necessary fields.


