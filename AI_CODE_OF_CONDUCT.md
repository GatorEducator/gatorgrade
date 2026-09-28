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

Instead of using `git commit -m`, type `git commit` to open your text
editor and format your message with the following structure:

1. **Subject:** Your standard conventional commit (e.g., `fix: ...`)
2. **Body:** A brief explanation of what AI generated and how you
   human-verified it.
3. **Trailer:** An `AI-Assisted:` tag at the very bottom.

**Example:**
```text
fix: update the over general exceptions in .pylintrc

Used GitHub Copilot to identify the specific exceptions needed. 
Manually verified the list against the pylint docs and ran local tests.

AI-Assisted: GitHub Copilot
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
