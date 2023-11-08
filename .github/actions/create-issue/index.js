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

    const prNumber = context.issue.number
    const comments = await client.rest.issues.listComments({
      owner: context.issue.owner,
      repo: context.issue.repo,
      issue_number: prNumber
    });

    issues = comments.data.filter(item => item.body.toLowerCase().startsWith("breaks: "))
    for (issue of issues) {
        await client.rest.issues.create({
            owner: context.issue.owner,
            repo: context.issue.repo,
            title: issue.body.replace(/^[Bb]reaks: /, ""),
            body: `This issue was created from a comment in Pull Request #${prNumber}.`
        })
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
