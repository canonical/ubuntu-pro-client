const core = require('@actions/core');
const github = require('@actions/github');

const commentHeader = (listName) => `<!-- ubuntu-pro-client-checklists-${listName} -->`;
const messageChangesCommentHeader = commentHeader("message-changes");

function createMessageChecklistCommentBody() {
    return `${messageChangesCommentHeader}
🌎 This PR changes translatable messages. 🌏

Please select which scenarios apply. For further explanation, please read our [policy on message changes](https://github.com/canonical/ubuntu-pro-client/blob/docs/dev-docs/explanations/string_changes_policy.md).
- [ ] New messages are being added.
    - We will ask translators to take a look and add translations if they have time, but it will not block this PR.
- [ ] Existing messages are being changed.
    - ⚠️ Please add a comment with justification of why messages are being altered.
    - If the changes are trivial (e.g. a typo fix), then translations must be preserved.
    - If the changes are substantial, then we will ask translators to take a look and update translations if they have time, but it will not block this PR.
- [ ] Existing messages are being deleted.
    - No special action needed.
`
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

    const files = await client.paginate(client.rest.pulls.listFiles, {
        owner: context.issue.owner,
        repo: context.issue.repo,
        pull_number: context.issue.number,
    });
    const comments = await client.rest.issues.listComments({
        owner: context.issue.owner,
        repo: context.issue.repo,
        issue_number: context.issue.number,
    });

    const filenames = files.map(f => f.filename);

    const modifiesMessages = filenames.includes("uaclient/messages/__init__.py")
    const theComment = comments.data.find(c => c.body.includes(messageChangesCommentHeader));

    console.log({modifiesMessages, commentExists: !!theComment});

    if (theComment && !modifiesMessages) {
        console.log("The comment already exists, but the PR no longer modifies messages. Deleting the comment.")
        client.rest.issues.deleteComment({
            owner: context.issue.owner,
            repo: context.issue.repo,
            comment_id: theComment.id
        });
    } else if (!theComment && modifiesMessages) {
        console.log("The comment doesn't exist, but the PR modifies messages. Creating the comment.")
        client.rest.issues.createComment({
            owner: context.issue.owner,
            repo: context.issue.repo,
            issue_number: context.issue.number,
            body: createMessageChecklistCommentBody(),
        });
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
