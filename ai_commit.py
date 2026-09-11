import json
import re
import subprocess
import urllib.error
import urllib.request


OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEY"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

MAX_DIFF_CHARS = 30000
MAX_HISTORY_COMMITS = 30


COMMIT_TYPES = (
    "feat",
    "fix",
    "docs",
    "refactor",
    "perf",
    "test",
    "chore",
    "build",
    "ci",
)

COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|refactor|perf|test|chore|build|ci)"
    r"(?:\([^)]+\))?"
    r"!?: .+$"
)


def run_git(*args):
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()

        raise RuntimeError(
            error or "Git command failed."
        )

    return result.stdout.strip()


def get_repository_root():
    return run_git(
        "rev-parse",
        "--show-toplevel",
    )


def get_staged_diff():
    return run_git(
        "diff",
        "--cached",
        "--no-ext-diff",
        "--unified=3",
    )


def get_staged_files():
    return run_git(
        "diff",
        "--cached",
        "--name-status",
    )


def get_recent_commits():
    try:
        return run_git(
            "log",
            f"-{MAX_HISTORY_COMMITS}",
            "--pretty=format:%s",
        )
    except RuntimeError:
        return ""


def build_context(
    staged_files,
    recent_commits,
    staged_diff,
):
    if len(staged_diff) > MAX_DIFF_CHARS:
        staged_diff = (
            staged_diff[:MAX_DIFF_CHARS]
            + "\n\n[DIFF TRUNCATED]\n"
        )

    if not recent_commits:
        recent_commits = (
            "(No previous commits available.)"
        )

    return f"""
Recent commits:

{recent_commits}

Staged files:

{staged_files}

Staged diff:

{staged_diff}
""".strip()


def call_openrouter(prompt):
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate Git Conventional Commit "
                    "messages. Follow the user's requested "
                    "output format exactly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0,
        "max_tokens": 180,
        "reasoning": {
            "enabled": False
        },
    }

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": (
                f"Bearer {OPENROUTER_API_KEY}"
            ),
            "Content-Type": "application/json",
            "HTTP-Referer": (
                "https://github.com/RealUnfazed"
            ),
            "X-OpenRouter-Title": (
                "AI Conventional Commit Generator"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            response_data = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        try:
            error_data = json.loads(body)

            error = error_data.get(
                "error",
                {}
            )

            if isinstance(error, dict):
                error_message = error.get(
                    "message",
                    body,
                )
            else:
                error_message = str(error)

        except json.JSONDecodeError:
            error_message = body

        raise RuntimeError(
            f"OpenRouter API error ({exc.code}): "
            f"{error_message}"
        )

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to OpenRouter: "
            f"{exc.reason}"
        )

    except TimeoutError:
        raise RuntimeError(
            "OpenRouter request timed out."
        )

    try:
        result = json.loads(response_data)

    except json.JSONDecodeError:
        raise RuntimeError(
            "OpenRouter returned invalid JSON."
        )

    if "error" in result:
        error = result["error"]

        if isinstance(error, dict):
            message = error.get(
                "message",
                "Unknown OpenRouter error.",
            )
        else:
            message = str(error)

        raise RuntimeError(
            f"OpenRouter API error: {message}"
        )

    choices = result.get("choices")

    if not choices:
        raise RuntimeError(
            "OpenRouter returned no choices."
        )

    content = (
        choices[0]
        .get("message", {})
        .get("content")
    )

    if not isinstance(content, str):
        raise RuntimeError(
            "OpenRouter returned no text content."
        )

    content = content.strip()

    if not content:
        raise RuntimeError(
            "OpenRouter returned empty content."
        )

    return content


def extract_lines(text):
    text = text.strip()

    text = re.sub(
        r"```(?:text|git|commit)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace(
        "```",
        "",
    )

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def clean_title(response):
    lines = extract_lines(response)

    for line in lines:
        line = re.sub(
            r"^[`\"']+|[`\"']+$",
            "",
            line,
        ).strip()

        if COMMIT_PATTERN.match(line):
            return line

    for line in lines:
        match = re.search(
            r"\b(feat|fix|docs|refactor|perf|test|chore|build|ci)"
            r"(?:\([^)]+\))?"
            r"!?: .+",
            line,
        )

        if match:
            candidate = match.group(0).strip()

            if COMMIT_PATTERN.match(candidate):
                return candidate

    raise RuntimeError(
        "The model did not return a valid Conventional Commit title.\n"
        f"Model output:\n{response}"
    )


def clean_description(response):
    lines = extract_lines(response)

    if not lines:
        raise RuntimeError(
            "The model returned an empty description."
        )

    description = " ".join(lines)

    description = re.sub(
        r"^[`\"']+|[`\"']+$",
        "",
        description,
    ).strip()

    if not description:
        raise RuntimeError(
            "The model returned an empty description."
        )

    return description


def validate_title(title):
    if not COMMIT_PATTERN.match(title):
        raise RuntimeError(
            "Invalid Conventional Commit title:\n"
            f"{title}"
        )


def generate_title(context):
    prompt = f"""
Generate ONE Git Conventional Commit TITLE.

Allowed types:

feat
fix
docs
refactor
perf
test
chore
build
ci

Rules:

- Describe only the actual staged changes.
- Do not invent functionality.
- Keep it concise.
- Use a scope only when useful.
- Use imperative wording.
- Do not include a body.
- Do not explain your reasoning.
- Output ONLY the title.
- Do not use Markdown.

Example:

feat: add user authentication

Context:

{context}
""".strip()

    return clean_title(
        call_openrouter(prompt)
    )


def generate_description(
    title,
    context,
):
    prompt = f"""
Generate ONE concise Git commit DESCRIPTION for this
Conventional Commit title:

{title}

Rules:

- Explain what changed and, when useful, why.
- Describe only the actual staged changes.
- Do not invent functionality.
- Keep it concise.
- Do not repeat the title.
- Do not include a heading.
- Do not use Markdown.
- Output ONLY the description.
- Use one or two concise sentences.

Context:

{context}
""".strip()

    return clean_description(
        call_openrouter(prompt)
    )


def edit_title(title):
    print()
    print("Current title:")
    print()
    print(f"  {title}")
    print()

    edited = input(
        "Edit title: "
    ).strip()

    if not edited:
        raise RuntimeError(
            "The commit title cannot be empty."
        )

    validate_title(edited)

    return edited


def edit_description(description):
    print()
    print("Current description:")
    print()
    print(f"  {description}")
    print()

    edited = input(
        "Edit description: "
    ).strip()

    if not edited:
        raise RuntimeError(
            "The commit description cannot be empty."
        )

    return edited


def choose_title(title):
    while True:
        print()
        print("Generated commit title:")
        print()
        print(f"  {title}")
        print()
        print("[Y] Yes")
        print("[E] Edit")
        print("[N] Cancel")
        print()

        answer = input(
            "Choose [Y/e/n]: "
        ).strip().lower()

        if answer in (
            "",
            "y",
            "yes",
        ):
            return title

        if answer in (
            "e",
            "edit",
        ):
            title = edit_title(title)
            continue

        if answer in (
            "n",
            "no",
            "q",
            "quit",
        ):
            print()
            print("Cancelled.")
            return None

        print()
        print("Please choose Y, E, or N.")


def choose_description(description):
    while True:
        print()
        print("Generated commit description:")
        print()
        print(f"  {description}")
        print()
        print("[Y] Yes")
        print("[E] Edit")
        print("[N] No description")
        print()
        
        answer = input(
            "Choose [Y/e/n]: "
        ).strip().lower()

        if answer in (
            "",
            "y",
            "yes",
        ):
            return description

        if answer in (
            "e",
            "edit",
        ):
            description = edit_description(
                description
            )
            continue

        if answer in (
            "n",
            "no",
        ):
            return None

        print()
        print("Please choose Y, E, or N.")


def create_commit(
    title,
    description=None,
):
    command = [
        "git",
        "commit",
        "-m",
        title,
    ]

    if description:
        command.extend(
            [
                "-m",
                description,
            ]
        )

    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return result.returncode


def main():
    try:
        repository_root = get_repository_root()
        staged_files = get_staged_files()
        staged_diff = get_staged_diff()
        recent_commits = get_recent_commits()

        if not staged_diff.strip():
            raise RuntimeError(
                "There are no staged changes."
            )

        context = build_context(
            staged_files,
            recent_commits,
            staged_diff,
        )

        print()
        print("Generating AI commit title...")
        print(f"Repository: {repository_root}")
        print(f"Model: {OPENROUTER_MODEL}")
        print()

        title = generate_title(
            context
        )

        title = choose_title(
            title
        )

        if title is None:
            return 0

        print()
        print("Generating AI commit description...")
        print()

        description = generate_description(
            title,
            context,
        )

        description = choose_description(
            description
        )

        print()
        print("Committing...")

        return create_commit(
            title,
            description,
        )

    except KeyboardInterrupt:
        print()
        print("Cancelled.")
        return 1

    except Exception as exc:
        print()
        print(
            "AI commit generation failed:"
        )
        print()
        print(str(exc))

        return 1


if __name__ == "__main__":
    raise SystemExit(main())

