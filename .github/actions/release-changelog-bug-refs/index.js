const fs = require('fs/promises');
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

    const client = github.getOctokit(
        core.getInput('repo-token', {required: true})
    );
    const commits = await client.rest.pulls.listCommits({
        owner: context.issue.owner,
        repo: context.issue.repo,
        pull_number: context.issue.number,
    });
    let lpBugs = [];
    let ghIssues = [];
    commits.data.forEach(commit => {
        const message = commit.commit.message.toLocaleUpperCase();
        lpBugs = lpBugs.concat(Array.from(message.matchAll(/LP: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/FIXES: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/CLOSES: #(\d+)/g)).map(m => m[1]));
    });
    const changelog = await fs.readFile("./debian/changelog", { encoding: "utf8" });
    const changelogEntries = changelog.split("ubuntu-advantage-tools");
    const newEntry = changelogEntries[1];
    const missingLpBugs = lpBugs.filter(bug => !newEntry.includes(`LP: #${bug}`));
    const missingGhIssues = ghIssues.filter(issue => !newEntry.includes(`GH: #${issue}`));

    if (missingLpBugs.length > 0 || missingGhIssues.length > 0) {
        core.setFailed({ missingLpBugs, missingGhIssues });
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
