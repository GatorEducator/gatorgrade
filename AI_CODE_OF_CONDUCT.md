# Artificial Intelligence Code of Conduct

## Our Pledge

In the interest of fostering responsible innovation and a welcoming
community, we as contributors and maintainers pledge to ensure that all
integration and use of Artificial Intelligence (AI) tools are aligned
with honesty, safety, respect, and accountability.

## Our Standards

Examples of behavior that contributes to responsible AI usage include:

- **Transparency:** Disclosing when code, documentation, or project
  communication are significantly generated or assisted by AI models.

- **Human Accountability:** Thoroughly reviewing, testing, and verifying
  all AI-generated contributions for technical accuracy, safety, and bias
  before submission.

- **Promoting Inclusivity:** Auditing AI outputs to ensure they adhere to
  respectful language and inclusive community standards.

### Documenting AI Usage in Commits

To fulfill our standards of Transparency and Human Accountability,
contributors must document AI assistance directly in their git commit
messages using a multi-line format (Subject, Body, and Trailer). 

You can format this easily in the terminal by stacking multiple `-m`
flags in your `git commit` command. Git will automatically separate
each flag with a blank line.

1. **First `-m` (Subject):** Your conventional commit message.
2. **Second `-m` (Body):** A brief explanation of what the AI generated
   and how you human-verified it.
3. **Third `-m` (Trailer):** An `AI-Assisted:` tag.

**Example:**
```bash
git commit -m "docs: add AI usage instructions to Code of Conduct" \
-m "Updated the Code of Conduct to explain how to format commit messages." \
-m "AI-Assisted: ChatGPT"
```

Examples of unacceptable AI usage include:

- Generating toxic, sexualized, abusive, or discriminatory text,
  imagery, or software outputs.

- Submitting low-effort, unverified, or hallucinated AI contributions
  without human validation.

- Utilizing AI to design security exploits, execute automated trolling,
  or target community members.

## Our Responsibilities

Project maintainers are responsible for establishing standards for
acceptable AI integration and taking fair corrective action against
misuse. Maintainers have the right to reject, modify, or remove content
that does not meet community standards.

## Scope

This AI Code of Conduct applies to all community members and contributors
to the gatorgrade or gatorgrader project. It applies in all project
spaces, including repositories, issue trackers, discussions, and other
collaborative venues.

## Enforcement

This Code of Conduct applies to the use of AI tools and assistants in the
gatorgrade or gatorgrader project. Project maintainers are responsible
for reviewing AI-generated contributions, including their accuracy,
safety, and appropriateness.

Instances where AI-generated content violates this Code of Conduct may be
addressed by:

- Requesting modifications or removal of the problematic content.
- Requiring human review and revision of AI contributions before
  acceptance.
- Restricting or prohibiting the use of specific AI tools in the project.
- Removing or reverting AI-generated contributions that do not meet
  standards.

Project maintainers have the right to refuse AI-generated contributions
that are inaccurate, plagiarized, harmful, or otherwise misaligned with
project values and quality standards. All AI usage is expected to be
transparent, accountable, and aligned with project values.
