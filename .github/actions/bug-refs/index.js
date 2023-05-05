const core = require('@actions/core');
const github = require('@actions/github');

const commentHeader = "<!-- ubuntu-pro-client-bug-refs -->";

function createCommentBody(commits, title) {
    let newComment = "";
    newComment += commentHeader;
    newComment += "\n";

    newComment += "Jira: ";
    const jiraMatches = title.toLocaleUpperCase().match(/SC-\d+/g);
    if (jiraMatches === null || jiraMatches.length === 0) {
        newComment += "This PR is not related to a Jira item. (The PR title does not include a SC-#### reference)\n";
    } else {
        const jiraID = jiraMatches[0];
        newComment += `[${jiraID}](https://warthogs.atlassian.net/browse/${jiraID})\n`;
    }
    newComment += "\n";

    let lpBugs = [];
    let ghIssues = [];
    commits.forEach(commit => {
        const message = commit.commit.message.toLocaleUpperCase();
        lpBugs = lpBugs.concat(Array.from(message.matchAll(/LP: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/FIXES: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/CLOSES: #(\d+)/g)).map(m => m[1]));
    });

    newComment += "GitHub Issues:";
    if (ghIssues.length === 0) {
        newComment += " No GitHub issues are fixed by this PR. (No commits have Fixes: #### references)\n";
    } else {
        newComment += "\n";
        ghIssues.forEach(issue => {
            newComment += `- Fixes: #${issue}\n`;
        });
    }
    newComment += "\n";

    newComment += "Launchpad Bugs:";
    if (lpBugs.length === 0) {
        newComment += " No Launchpad bugs are fixed by this PR. (No commits have LP: #### references)\n";
    } else {
        newComment += "\n";
        lpBugs.forEach(bug => {
            newComment += `- LP: [#${bug}](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/${bug})\n`;
        });
    }
    newComment += "\n";

    newComment += "👍 this comment to confirm that this is correct.";

    return newComment;
}

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
    const comments = await client.rest.issues.listComments({
        owner: context.issue.owner,
        repo: context.issue.repo,
        issue_number: context.issue.number,
    });
    const theComment = comments.data.find(c => c.body.includes(commentHeader));
    if (theComment) {
        // comment already exists, update it appropriately
        const existingBody = theComment.body;
        const newBody = createCommentBody(commits.data, context.payload.pull_request.title);
        if (existingBody !== newBody) {
            client.rest.issues.updateComment({
                owner: context.issue.owner,
                repo: context.issue.repo,
                comment_id: theComment.id,
                body: newBody,
            });
        }
    } else {
        // first run, comment doesn't exist yet
        const newBody = createCommentBody(commits.data, context.payload.pull_request.title);
        client.rest.issues.createComment({
            owner: context.issue.owner,
            repo: context.issue.repo,
            issue_number: context.issue.number,
            body: newBody,
        });
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
