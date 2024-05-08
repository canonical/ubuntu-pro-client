const fs = require('fs');
const core = require('@actions/core');
const github = require('@actions/github');

const commentHeader = "<!-- ubuntu-pro-client-release-checklists -->";
const commentSectionHeader = (name) => `<!-- ubuntu-pro-client-release-checklists-${name}-header -->`;
const commentSectionFooter = (name) => `<!-- ubuntu-pro-client-release-checklists-${name}-footer -->`;

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
    
    
    let lpBugs = [];
    let ghIssues = [];
    commits.forEach(commit => {
        const message = commit.commit.message.toLocaleUpperCase();
        lpBugs = lpBugs.concat(Array.from(message.matchAll(/LP: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/FIXES: #(\d+)/g)).map(m => m[1]));
        ghIssues = ghIssues.concat(Array.from(message.matchAll(/CLOSES: #(\d+)/g)).map(m => m[1]));
    });
    const changelog = fs.readFileSync("./debian/changelog", { encoding: "utf8" });
    const changelogEntries = changelog.split(/^ubuntu-advantage-tools \(/);
    const newEntry = changelogEntries[1];
    const includedLpBugs = lpBugs.filter(bug => newEntry.includes(`LP: #${bug}`));
    const includedGhIssues = ghIssues.filter(issue => newEntry.includes(`GH: #${issue}`));
    const missingLpBugs = lpBugs.filter(bug => !newEntry.includes(`LP: #${bug}`));
    const missingGhIssues = ghIssues.filter(issue => !newEntry.includes(`GH: #${issue}`));
    
    const includedBugRefs = []
    includedGhIssues.forEach(issue => {
        includedBugRefs.push(`GitHub: #${issue}`)
    });
    includedLpBugs.forEach(bug => {
        includedBugRefs.push(`Launchpad: [#${bug}](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/${bug})`);
    });
    
    const missingBugRefs = []
    missingGhIssues.forEach(issue => {
        missingBugRefs.push(`GitHub: #${issue}`)
    });
    missingLpBugs.forEach(bug => {
        missingBugRefs.push(`Launchpad: [#${bug}](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/${bug})`);
    });
    
    let section = header;
    
    section += "\n\n### Bug References\n\n";
    
    section += "\n\n#### Included in changelog\n\n";
    
    
    if (includedBugRefs.length > 0) {
        includedBugRefs.forEach(refString => {
            section += `- ${refString}\n`
        });
    } else {
        section += "None.\n"
    }
    
    section += "\n\n#### Fixed but not in changelog\n\n";
    
    if (missingBugRefs.length > 0) {
        missingBugRefs.forEach(refString => {
            section += `- ${refString}\n`
        });
    } else {
        section += "None.\n"
    }

    section += "\n\n#### Confirm\n\n";

    const check = verified ? "x" : " ";
    section += `- [${check}] I've properly referenced all worthy bugs in the changelog`;
    
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
    comment += "\n\n## Release Checklist\n\n"
    comment += createBugRefsSection({
        prTitle,
        commits,
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
