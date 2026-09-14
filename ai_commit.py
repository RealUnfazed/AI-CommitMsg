import argparse
import json
import os
import re
import subprocess
import threading
import urllib.error
import urllib.request


SCRIPT_DIRECTORY = os.path.dirname(
    os.path.abspath(__file__)
)

ENV_FILE = os.path.join(
    SCRIPT_DIRECTORY,
    ".env",
)


DEFAULTS = {
    "OPENROUTER_API_KEY": "",
    "OPENROUTER_MODEL": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "OPENROUTER_FALLBACK_MODELS": "",
    "OPENROUTER_URL": "https://openrouter.ai/api/v1/chat/completions",
    "OPENROUTER_HTTP_REFERER": "https://github.com/RealUnfazed",
    "OPENROUTER_TITLE": "AI Conventional Commit Generator",
    "MAX_DIFF_CHARS": "30000",
    "MAX_HISTORY_COMMITS": "30",
    "MAX_TOKENS": "180",
    "REQUEST_TIMEOUT": "120",
    "TEMPERATURE": "0",
}


def load_env_file(path):
    values = {}

    if not os.path.isfile(path):
        return values

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            for raw_line in file:
                line = raw_line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split(
                    "=",
                    1,
                )

                key = key.strip()
                value = value.strip()

                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in (
                        '"',
                        "'",
                    )
                ):
                    value = value[1:-1]

                values[key] = value

    except OSError as exc:
        raise RuntimeError(
            f"Could not read .env file: {exc}"
        )

    return values


ENV_VALUES = load_env_file(
    ENV_FILE
)


def get_config(name):
    if name in os.environ:
        return os.environ[name]

    if name in ENV_VALUES:
        return ENV_VALUES[name]

    return DEFAULTS.get(
        name,
        "",
    )


OPENROUTER_API_KEY = get_config(
    "OPENROUTER_API_KEY"
)

OPENROUTER_URL = get_config(
    "OPENROUTER_URL"
)

OPENROUTER_HTTP_REFERER = get_config(
    "OPENROUTER_HTTP_REFERER"
)

OPENROUTER_TITLE = get_config(
    "OPENROUTER_TITLE"
)

DEFAULT_MODEL = get_config(
    "OPENROUTER_MODEL"
)

FALLBACK_MODELS = [
    model.strip()
    for model in get_config(
        "OPENROUTER_FALLBACK_MODELS"
    ).split(",")
    if model.strip()
]

MAX_DIFF_CHARS = int(
    get_config("MAX_DIFF_CHARS")
)

MAX_HISTORY_COMMITS = int(
    get_config("MAX_HISTORY_COMMITS")
)

MAX_TOKENS = int(
    get_config("MAX_TOKENS")
)

REQUEST_TIMEOUT = int(
    get_config("REQUEST_TIMEOUT")
)

TEMPERATURE = float(
    get_config("TEMPERATURE")
)


COMMIT_TYPES = (
    "initial",
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
    "security",
    "deps",
    "release",
)


COMMIT_TYPES_PATTERN = "|".join(
    re.escape(commit_type)
    for commit_type in COMMIT_TYPES
)


COMMIT_PATTERN = re.compile(
    rf"^({COMMIT_TYPES_PATTERN})"
    r"(?:\([^)]+\))?"
    r"!?: .+$"
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Generate Conventional Commit messages "
            "using OpenRouter."
        )
    )

    parser.add_argument(
        "--model",
        dest="model",
        default=None,
        help=(
            "Override the OpenRouter model for this run."
        ),
    )

    return parser.parse_args()


def get_models(selected_model=None):
    models = []

    if selected_model:
        models.append(
            selected_model.strip()
        )
    else:
        if DEFAULT_MODEL:
            models.append(
                DEFAULT_MODEL.strip()
            )

        for model in FALLBACK_MODELS:
            if model not in models:
                models.append(model)

    models = [
        model
        for model in models
        if model
    ]

    if not models:
        raise RuntimeError(
            "No OpenRouter models are configured."
        )

    return models


def run_git(*args):
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        error = (
            result.stderr.strip()
            or result.stdout.strip()
        )

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


def is_retryable_api_error(status_code):
    return status_code in (
        408,
        409,
        425,
        429,
        500,
        502,
        503,
        504,
    )


def extract_api_error(body):
    try:
        error_data = json.loads(body)

        error = error_data.get(
            "error",
            {},
        )

        if isinstance(error, dict):
            message = error.get(
                "message",
                body,
            )

            code = error.get(
                "code"
            )

            if code:
                return (
                    f"{message} "
                    f"(code: {code})"
                )

            return str(message)

        return str(error)

    except json.JSONDecodeError:
        return body.strip() or "Unknown API error."


def call_openrouter(
    prompt,
    models,
):
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured.\n"
            f"Set it in:\n{ENV_FILE}"
        )

    errors = []

    for model in models:
        print(
            f"Using model: {model}"
        )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate Git Conventional "
                        "Commit messages. Follow the "
                        "user's requested output format "
                        "exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "reasoning": {
                "enabled": False
            },
        }

        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(
                payload
            ).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": (
                    f"Bearer {OPENROUTER_API_KEY}"
                ),
                "Content-Type": (
                    "application/json"
                ),
                "HTTP-Referer": (
                    OPENROUTER_HTTP_REFERER
                ),
                "X-OpenRouter-Title": (
                    OPENROUTER_TITLE
                ),
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                response_data = (
                    response.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            error_message = extract_api_error(
                body
            )

            if is_retryable_api_error(
                exc.code
            ):
                errors.append(
                    f"{model}: "
                    f"OpenRouter returned "
                    f"{exc.code}: "
                    f"{error_message}"
                )

                print(
                    f"Model failed ({exc.code}), "
                    "trying next model..."
                )

                continue

            raise RuntimeError(
                f"OpenRouter API error "
                f"({exc.code}) using {model}: "
                f"{error_message}"
            )

        except urllib.error.URLError as exc:
            errors.append(
                f"{model}: "
                f"Could not connect to OpenRouter: "
                f"{exc.reason}"
            )

            print(
                "Connection failed, "
                "trying next model..."
            )

            continue

        except TimeoutError:
            errors.append(
                f"{model}: "
                "OpenRouter request timed out."
            )

            print(
                "Request timed out, "
                "trying next model..."
            )

            continue

        except OSError as exc:
            errors.append(
                f"{model}: "
                f"Network error: {exc}"
            )

            print(
                "Network error, "
                "trying next model..."
            )

            continue

        try:
            result = json.loads(
                response_data
            )

        except json.JSONDecodeError:
            errors.append(
                f"{model}: "
                "OpenRouter returned invalid JSON."
            )

            print(
                "Invalid response, "
                "trying next model..."
            )

            continue

        if "error" in result:
            error = result["error"]

            if isinstance(error, dict):
                message = error.get(
                    "message",
                    "Unknown OpenRouter error.",
                )

                code = error.get(
                    "code"
                )
            else:
                message = str(error)
                code = None

            if (
                isinstance(code, int)
                and is_retryable_api_error(code)
            ):
                errors.append(
                    f"{model}: "
                    f"OpenRouter API error "
                    f"{code}: {message}"
                )

                print(
                    f"Model failed ({code}), "
                    "trying next model..."
                )

                continue

            raise RuntimeError(
                f"OpenRouter API error using "
                f"{model}: {message}"
            )

        choices = result.get(
            "choices"
        )

        if not choices:
            errors.append(
                f"{model}: "
                "OpenRouter returned no choices."
            )

            print(
                "No choices returned, "
                "trying next model..."
            )

            continue

        content = (
            choices[0]
            .get("message", {})
            .get("content")
        )

        if not isinstance(
            content,
            str,
        ):
            errors.append(
                f"{model}: "
                "OpenRouter returned no text content."
            )

            print(
                "No text returned, "
                "trying next model..."
            )

            continue

        content = content.strip()

        if not content:
            errors.append(
                f"{model}: "
                "OpenRouter returned empty content."
            )

            print(
                "Empty response, "
                "trying next model..."
            )

            continue

        return content

    error_text = "\n".join(
        f"- {error}"
        for error in errors
    )

    raise RuntimeError(
        "All configured OpenRouter models failed.\n\n"
        f"{error_text}"
    )


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
    lines = extract_lines(
        response
    )

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
            rf"\b({COMMIT_TYPES_PATTERN})"
            r"(?:\([^)]+\))? !?: .+",
            line,
        )

        if match:
            candidate = match.group(
                0
            ).strip()

            if COMMIT_PATTERN.match(
                candidate
            ):
                return candidate

    raise RuntimeError(
        "The model did not return a valid "
        "Conventional Commit title.\n"
        f"Model output:\n{response}"
    )


def clean_description(response):
    lines = extract_lines(
        response
    )

    if not lines:
        raise RuntimeError(
            "The model returned an empty description."
        )

    description = " ".join(
        lines
    )

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
    if not COMMIT_PATTERN.match(
        title
    ):
        raise RuntimeError(
            "Invalid Conventional Commit title:\n"
            f"{title}"
        )


def generate_title(
    context,
    models,
):
    allowed_types = "\n".join(
        COMMIT_TYPES
    )

    prompt = f"""
Generate ONE Git Conventional Commit TITLE.

Allowed types:

{allowed_types}

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
        call_openrouter(
            prompt,
            models,
        )
    )


def generate_description(
    context,
    models,
):
    prompt = f"""
Generate ONE concise Git commit DESCRIPTION.

Rules:

- Explain what changed and, when useful, why.
- Describe only the actual staged changes.
- Do not invent functionality.
- Keep it concise.
- Do not include a heading.
- Do not use Markdown.
- Output ONLY the description.
- Use one or two concise sentences.
- Do not output a Conventional Commit title.

Context:

{context}
""".strip()

    return clean_description(
        call_openrouter(
            prompt,
            models,
        )
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

    validate_title(
        edited
    )

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


def choose_generation_mode():
    while True:
        print()
        print(
            "What do you want to generate?"
        )
        print()
        print("[1] Title only")
        print("[2] Title + description")
        print("[N] Cancel")
        print()

        answer = input(
            "Choose [1/2/n]: "
        ).strip().lower()

        if answer in (
            "1",
            "title",
            "title only",
        ):
            return "title"

        if answer in (
            "2",
            "both",
            "title + description",
        ):
            return "both"

        if answer in (
            "",
            "n",
            "no",
            "q",
            "quit",
            "cancel",
        ):
            print()
            print("Cancelled.")
            return None

        print()
        print(
            "Please choose 1, 2, or N."
        )


def choose_title(title):
    while True:
        print()
        print(
            "Generated commit title:"
        )
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
            title = edit_title(
                title
            )

            continue

        if answer in (
            "n",
            "no",
            "q",
            "quit",
            "cancel",
        ):
            print()
            print("Cancelled.")

            return None

        print()
        print(
            "Please choose Y, E, or N."
        )


def choose_description(
    description
):
    while True:
        print()
        print(
            "Generated commit description:"
        )
        print()
        print(
            f"  {description}"
        )
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
            "skip",
        ):
            return None

        print()
        print(
            "Please choose Y, E, or N."
        )


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


class BackgroundGeneration:
    def __init__(
        self,
        function,
    ):
        self.function = function
        self.result = None
        self.error = None
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
        )

    def _run(self):
        try:
            self.result = self.function()

        except Exception as exc:
            self.error = exc

    def start(self):
        self.thread.start()

    def wait(self):
        self.thread.join()

        if self.error:
            raise self.error

        return self.result

    def is_finished(self):
        return not self.thread.is_alive()


def main():
    try:
        args = parse_arguments()

        repository_root = (
            get_repository_root()
        )

        staged_files = (
            get_staged_files()
        )

        staged_diff = (
            get_staged_diff()
        )

        recent_commits = (
            get_recent_commits()
        )

        if not staged_diff.strip():
            raise RuntimeError(
                "There are no staged changes."
            )

        context = build_context(
            staged_files,
            recent_commits,
            staged_diff,
        )

        models = get_models(
            args.model
        )

        print()
        print(
            "AI Conventional Commit"
        )
        print(
            f"Repository: {repository_root}"
        )
        print(
            f"Primary model: {models[0]}"
        )

        if len(models) > 1:
            print(
                f"Fallback models: "
                f"{len(models) - 1}"
            )

        mode = choose_generation_mode()

        if mode is None:
            return 0

        print()
        print(
            "Generating AI commit title..."
        )

        title = generate_title(
            context,
            models,
        )

        description_task = None

        if mode == "both":
            print()
            print(
                "Generating AI commit description "
                "in the background..."
            )

            description_task = (
                BackgroundGeneration(
                    lambda: generate_description(
                        context,
                        models,
                    )
                )
            )

            description_task.start()

        title = choose_title(
            title
        )

        if title is None:
            return 0

        description = None

        if mode == "both":
            print()

            if description_task.is_finished():
                print(
                    "Description is ready."
                )
            else:
                print(
                    "Waiting for the description..."
                )

            description = (
                description_task.wait()
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
    raise SystemExit(
        main()
    )