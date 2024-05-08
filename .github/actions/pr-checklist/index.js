const core = require('@actions/core');
const github = require('@actions/github');

const commentHeader = "<!-- ubuntu-pro-client-checklists -->";
const commentSectionHeader = (name) => `<!-- ubuntu-pro-client-checklists-${name}-header -->`;
const commentSectionFooter = (name) => `<!-- ubuntu-pro-client-checklists-${name}-footer -->`;

function getCommentSection(name, body) {
    const header = commentSectionHeader(name);
    const footer = commentSectionFooter(name);
    try {
        return body.split(header)[1].split(footer)[0];
    } catch {
        console.warn(`Failed to get "${name}" section of comment`);
        return "";
    }
}


const BUG_REFS = "bug-refs";
function bugRefsVerified(existingSection) {
    return existingSection.includes("- [x]")
}
function createBugRefsSection({
    prTitle,
    commits,
    existingBody,
}) {
    const header = commentSectionHeader(BUG_REFS);
    const footer = commentSectionFooter(BUG_REFS);
    const existingSection = existingBody ? getCommentSection(BUG_REFS, existingBody) : null;
    const verified = existingSection ? bugRefsVerified(existingSection) : false;
    
    const bugRefs = []
    
    const jiraMatches = prTitle.toLocaleUpperCase().match(/SC-\d+/g);
    if (jiraMatches) {
        const jiraID = jiraMatches[0];
        bugRefs.push(`Jira: [${jiraID}](https://warthogs.atlassian.net/browse/${jiraID})`);
    }
    let lpBugs = [];
    let ghIssues = [];
    commits.forEach(commit => {
        const message = commit.commit.message.toLocaleUpperCase();
        lpBugs = lpBugs.concat(Array.from(message.matchAll(/LP: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/FIXES: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/CLOSES: #(\d+)/g)).map(m => m[1]));
    });
    ghIssues.forEach(issue => {
        bugRefs.push(`GitHub: #${issue}`)
    });
    lpBugs.forEach(bug => {
        bugRefs.push(`Launchpad: [#${bug}](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/${bug})`);
    });
    
    let section = header;
    
    section += "\n\n### Bug References\n\n";
    
    if (bugRefs.length > 0) {
        bugRefs.forEach(refString => {
            section += `- ${refString}\n`
        });
    } else {
        section += "None.\n"
    }
    
    section += "\n\n#### Confirm\n\n";

    const check = verified ? "x" : " ";
    section += `- [${check}] I've properly referenced all bugs that this PR fixes`;
    
    section += `
<details>
  <summary>How to properly reference fixed bugs</summary>

* If this PR is related to a Jira item, include an \`SC-1234\` reference in the PR title
* If this PR is fixes a GitHub issue, include a \`Fixes: #1234\` reference in the commit that fixes the issue
* If this PR is fixes a Launchpad bug, include a \`LP: #12345678\` reference in the commit that fixes the issue
  
</details>`
    
    section += footer;
    return section;
}


const TEST_UPDATES = "test-updates";
const unitTestsUpdated = "I have updated or added any unit tests accordingly"
const unitTestsNotUpdated = "No unit test changes are necessary for this change"
const integrationTestsUpdated = "I have updated or added any integration tests accordingly"
const integrationTestsNotUpdated = "No integration test changes are necessary for this change"
function testUpdatesVerified(existingSection) {
    return (
        existingSection.includes(`- [x] ${unitTestsUpdated}`) 
        ||  existingSection.includes(`- [x] ${unitTestsNotUpdated}`) 
    ) && (
        existingSection.includes(`- [x] ${integrationTestsUpdated}`)
        ||  existingSection.includes(`- [x] ${integrationTestsNotUpdated}`) 
    )
}
function createTestUpdatesSection({
    existingBody,
}) {
    const header = commentSectionHeader(TEST_UPDATES);
    const footer = commentSectionFooter(TEST_UPDATES);
    const existingSection = existingBody ? getCommentSection(TEST_UPDATES, existingBody) : null;
    const unitTestCheck = existingSection.includes(`- [x] ${unitTestsUpdated}`) ? "x" : " "
    const unitTestNotCheck = existingSection.includes(`- [x] ${unitTestsNotUpdated}`) ? "x" : " "
    const integrationTestCheck = existingSection.includes(`- [x] ${integrationTestsUpdated}`) ? "x" : " "
    const integrationTestNotCheck = existingSection.includes(`- [x] ${integrationTestsNotUpdated}`) ? "x" : " "
    
    let section = header;
    
    section += "\n\n### Test Updates\n\n";
    
    section += "#### Unit Tests\n\n";
    section += `- [${unitTestCheck}] ${unitTestsUpdated}\n`;
    section += `- [${unitTestNotCheck}] ${unitTestsNotUpdated}\n`;

    section += "#### Integration Tests\n\n";
    section += `- [${integrationTestCheck}] ${integrationTestsUpdated}\n`;
    section += `- [${integrationTestNotCheck}] ${integrationTestsNotUpdated}\n`;
    
    section += footer;
    return section;
}


const DOCS = "docs";
const docsUpdated = "Changes here need to be documented and I have referenced the docs PR in the description"
const docsNotUpdated = "No documentation updates are necessary for this change"
function docsVerified(existingSection) {
    return (
        existingSection.includes(`- [x] ${docsUpdated}`) 
        ||  existingSection.includes(`- [x] ${docsNotUpdated}`) 
    )
}
function createDocsSection({
    existingBody,
}) {
    const header = commentSectionHeader(DOCS);
    const footer = commentSectionFooter(DOCS);
    const existingSection = existingBody ? getCommentSection(DOCS, existingBody) : null;
    const docsCheck = existingSection.includes(`- [x] ${docsUpdated}`) ? "x" : " "
    const docsNotCheck = existingSection.includes(`- [x] ${docsNotUpdated}`) ? "x" : " "
    
    let section = header;
    
    section += "\n\n### Documentation\n\n";
    
    section += `- [${docsCheck}] ${docsUpdated}\n`;
    section += `- [${docsNotCheck}] ${docsNotUpdated}\n`;

    section += footer;
    return section;
}


const EXTRA_REVIEWS = "extra-reviews";
const extraReviewsNeeded = "Yes, and I have requested those reviews via GitHub"
const extraReviewsNotNeeded= "No"
function extraReviewsVerified(existingSection) {
    return (
        existingSection.includes(`- [x] ${extraReviewsNeeded}`) 
        ||  existingSection.includes(`- [x] ${extraReviewsNotNeeded}`) 
    )
}
function createExtraReviewsSection({
    existingBody,
}) {
    const header = commentSectionHeader(EXTRA_REVIEWS);
    const footer = commentSectionFooter(EXTRA_REVIEWS);
    const existingSection = existingBody ? getCommentSection(EXTRA_REVIEWS, existingBody) : null;
    const extraReviewsCheck = existingSection.includes(`- [x] ${extraReviewsNeeded}`) ? "x" : " "
    const extraReviewsNotCheck = existingSection.includes(`- [x] ${extraReviewsNotNeeded}`) ? "x" : " "
    
    let section = header;
    
    section += "\n\n### Does this PR require review from someone outside the core ubuntu-pro-client team?\n\n";
    
    section += `- [${extraReviewsCheck}] ${extraReviewsNeeded}\n`;
    section += `- [${extraReviewsNotCheck}] ${extraReviewsNotNeeded}\n`;

    section += footer;
    return section;
}


function createComment({
    prTitle,
    prDescription,
    commits,
    files,
    existingBody,
}) {
    let comment = `${commentHeader}`;
    comment += `

## PR Checklist

<details>
  <summary>How to use this checklist</summary>
  
  ### How to use this checklist

  #### PR Author
  
  For each section, check a box when it is true.
  Uncheck a box if it becomes un-true.
  Then check the box at the bottom of the PR description to re-run the action that creates this checklist.
  The action that creates and updates this comment will retain your edits.
  The action will fail if the checklist is not completed.
  
  #### PR Reviewer
  
  Check that the PR checklist action did not fail.
  Double check that the author filled out the checklist accurately.
  If you disagree with a checklist item, start a conversation.
  For example, the author may say they don't think integration tests are necessary, but you may disagree.
  
</details>`
    comment += createBugRefsSection({
        prTitle,
        commits,
        existingBody,
    });
    comment += createTestUpdatesSection({
        existingBody,
    });
    comment += createDocsSection({
        existingBody,
    });
    comment += createExtraReviewsSection({
        existingBody,
    });
    return comment;
}

async function run() {
    const context = github.context;
    if (context.eventName !== "pull_request") {
      console.log(
        'The event that triggered this action was not a pull request, skipping.'
      );
      return;
    }
    
    const prTitle = context.payload.pull_request.title;
    const prDescription = context.payload.pull_request.body;

    const client = github.getOctokit(
        core.getInput('repo-token', {required: true})
    );

    const files = (await client.paginate(client.rest.pulls.listFiles, {
        owner: context.issue.owner,
        repo: context.issue.repo,
        pull_number: context.issue.number,
    })).data;
    const comments = (await client.rest.issues.listComments({
        owner: context.issue.owner,
        repo: context.issue.repo,
        issue_number: context.issue.number,
    })).data;
    const commits = (await client.rest.pulls.listCommits({
        owner: context.issue.owner,
        repo: context.issue.repo,
        pull_number: context.issue.number,
    })).data;

    const theComment = comments.find(c => c.body.includes(commentHeader));
    
    const errors = [];

    if (theComment) {
        // comment already exists, update it appropriately
        const existingBody = theComment.body;
        if (!bugRefsVerified(getCommentSection(BUG_REFS, existingBody))) {
            errors.push("Bug references list has not been confirmed.")
        }
        if (!testUpdatesVerified(getCommentSection(TEST_UPDATES, existingBody))) {
            errors.push("Test updates section has not been filled out.")
        }
        if (!docsVerified(getCommentSection(DOCS, existingBody))) {
            errors.push("Documentation section has not been filled out.")
        }
        if (!extraReviewsVerified(getCommentSection(EXTRA_REVIEWS, existingBody))) {
            errors.push("Extra reviews section has not been filled out.")
        }
        const newBody = createComment({
            prTitle,
            prDescription,
            commits,
            files,
            existingBody,
        })
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
        const newBody = createComment({
            prTitle,
            prDescription,
            commits,
            files,
            existingBody: null,
        })
        client.rest.issues.createComment({
            owner: context.issue.owner,
            repo: context.issue.repo,
            issue_number: context.issue.number,
            body: newBody,
        });
        client.rest.reactions.createForIssue({
            owner: context.issue.owner,
            repo: context.issue.repo,
            issue_number: context.issue.number,
            content: "eyes"
        });
    }
    
    if (errors.length > 0) {
        throw new Error(JSON.stringify({errors}, null, 2));
    }
}

run().catch(error => {
    console.error(error);
    core.setFailed(error.message);
})
