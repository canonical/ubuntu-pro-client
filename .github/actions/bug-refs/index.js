const core = require('@actions/core');
const github = require('@actions/github');

async function run() {
    const context = github.context;
    if (context.eventName !== "pull_request") {
      console.log(
        'The event that triggered this action was not a pull request, skipping.'
      );
      return;
    }

    const body = context.payload.pull_request.body.toLocaleUpperCase();
    const ignoreJira = body.includes("NO-JIRA");
    const ignoreLaunchpad = body.includes("NO-LP");
    const ignoreGithub = body.includes("NO-GH");

    const errorMessages = [];

    const title = context.payload.pull_request.title;
    if (!ignoreJira && !title.toLocaleUpperCase().includes("SC-")) {
        errorMessages.push("The PR title does not include a Jira SC-#### reference.\nEither add one or add 'no-jira' to the PR description.");
    }

    const client = github.getOctokit(
        core.getInput('repo-token', {required: true})
    );
    const commits = await client.rest.pulls.listCommits({
        owner: context.issue.owner,
        repo: context.issue.repo,
        pull_number: context.issue.number,
    });

    let launchpadPresent = false;
    let githubPresent = false;
    commits.data.forEach(commit => {
        const message = commit.commit.message.toLocaleUpperCase();
        if (message.includes("LP: #")) {
            launchpadPresent = true;
        }
        if (message.includes("FIXES: #") || message.includes("CLOSES: #")) {
            githubPresent = true;
        }
    });

    if (!ignoreLaunchpad && !launchpadPresent) {
        errorMessages.push("None of the commits include a Launchpad bug reference.\nEither add one or add 'no-lp' to the PR description.");
    }
    if (!ignoreGithub && !githubPresent) {
        errorMessages.push("None of the commits include a Github bug reference.\nEither add one or add 'no-gh' to the PR description.");
    }

    if (errorMessages.length > 0) {
        core.setFailed(errorMessages.join("\n\n"));
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
