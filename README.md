# 🤖 AI Conventional Commit

An AI-powered Git commit assistant that analyzes your **staged changes** and generates a Conventional Commit title and description using [OpenRouter](https://openrouter.ai/).

Instead of staring at a diff trying to figure out what to write, run:

```bash
git add .
git aicommit
```

The AI generates the commit **title first**, lets you review or edit it, then generates a **description** and lets you review, edit, or skip it before creating the commit.

No Git editor. No Vim. No commit-message template.

---

## ✨ Features

- 🤖 AI-generated Conventional Commit titles
- 📝 AI-generated commit descriptions
- ✏️ Edit the title before committing
- ✏️ Edit the description before committing
- ⏭️ Skip the description and commit with the title only
- 🔍 Analyzes staged files and the actual staged diff
- 🧠 Uses recent commit history for context
- 📏 Keeps generated commit titles concise
- 🧩 Supports Conventional Commit types, scopes, and breaking changes
- ⚡ Runs directly through a simple Git alias
- 🌐 Uses OpenRouter's API
- 🪶 No framework or heavy dependencies
- 🚫 No Git hook required

---

## 🚀 How It Works

The workflow is intentionally split into two stages.

```text
                    git aicommit
                         │
                         ▼
                Analyze staged changes
                         │
                         ▼
                 Generate title
                         │
              ┌──────────┼──────────┐
              ▼          ▼           ▼
             Yes        Edit         No
              │          │           │
              │          ▼           │
              │     Review again     │
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
                Generate description
                         │
              ┌──────────┼──────────┐
              ▼          ▼           ▼
             Yes        Edit         No
              │          │           │
              │          ▼           │
              │     Review again     │
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
                    git commit
```

### Example

```text
Generating AI commit title...

Generated commit title:

  feat: add AI commit generation

[Y] Yes
[E] Edit
[N] Cancel

Choose [Y/e/n]: y


Generating AI commit description...

Generated commit description:

  Add an OpenRouter-powered workflow that analyzes staged
  changes and creates Conventional Commit messages.

[Y] Yes
[E] Edit
[N] No description

Choose [Y/e/n]: y


Committing...

[master 4c91a2f] feat: add AI commit generation
```

If you choose **N** for the description, the commit still happens:

```text
feat: add AI commit generation
```

The description is simply omitted.

---

## 🧠 What the AI Sees

The generator builds its context from your repository instead of asking the model to blindly guess what changed.

It provides:

### 📂 Staged files

For example:

```text
M       README.md
A       tools/ai_commit.py
```

### 🔀 Staged diff

The actual output of:

```bash
git diff --cached
```

This is the primary source of truth for the generated commit.

### 📜 Recent commits

Recent commit subjects are also provided so the generated message can better match the existing style of the repository.

The diff is limited to a reasonable size before being sent to the API to avoid unnecessarily huge requests.

---

## 📋 Conventional Commits

Generated titles follow the Conventional Commits format:

```text
<type>: <description>
```

Supported types:

```text
feat
fix
docs
refactor
perf
test
chore
build
ci
```

### Examples

```text
feat: add user authentication
```

```text
fix: prevent duplicate API requests
```

```text
docs: update installation instructions
```

```text
refactor(auth): simplify login flow
```

```text
perf: reduce image processing overhead
```

Breaking changes are also supported:

```text
feat!: remove legacy authentication API
```

or:

```text
feat(api)!: change response format
```

---

## ⚙️ Setup

### Requirements

- Git
- Python 3
- An OpenRouter API key
- A repository with staged changes

No Python packages are required.

The project uses Python's built-in libraries for:

- Git commands
- HTTP requests
- JSON handling
- Input/output

---

## 🔑 OpenRouter

The generator communicates with OpenRouter using its OpenAI-compatible chat completions API.

The configured model is:

```text
nvidia/nemotron-3-ultra-550b-a55b:free
```

Set your OpenRouter API key in:

```text
tools/ai_commit.py
```

```python
OPENROUTER_API_KEY = "your-api-key"
```

---

## 🛠️ Git Alias

The project is designed to be used through:

```bash
git aicommit
```

Configure the alias:

```powershell
git config --global alias.aicommit '!python "C:/path/to/ai_commit.py"'
```

For example:

```powershell
git config --global alias.aicommit '!python "C:/Users/Unfazed/Documents/Python/AI-CommitMsg/ai_commit.py"'
```

Check that Git recognizes it:

```powershell
git aicommit
```

---

### Already Have an `aicommit` Alias or Wanna remove Alias?

The Git alias is **global**, so if you already configured `aicommit` for another project, remove the old alias first:

```powershell
git config --global --unset alias.aicommit
```

Then configure it again with the path to this project's `ai_commit.py`:

```powershell
git config --global alias.aicommit '!python "C:/path/to/ai_commit.py"'
```

You can verify the current alias with:

```powershell
git config --global --get alias.aicommit
```

## 📦 Usage

Stage the changes you want included:

```bash
git add .
```

Then run:

```bash
git aicommit
```

### Don't use:

```bash
git commit
```

for the AI workflow.

Normal Git commits still work normally, but `git aicommit` is the command that invokes the AI generator.

---

## ✏️ Editing

### Edit the title

If the generated title isn't quite right:

```text
[E] Edit
```

You can enter a replacement title.

The replacement is validated against the Conventional Commit format before continuing.

### Edit the description

The same applies to the generated description:

```text
[E] Edit
```

You can rewrite it before committing.

### Skip the description

Choosing:

```text
[N] No description
```

does **not** cancel the commit.

The commit is created using the title only:

```text
feat: add AI commit generation
```

---

## 🧩 Project Structure

```text
ai-conventional-commit/
│
├── tools/
│   └── ai_commit.py
│
├── .gitignore
├── README.md
└── LICENSE
```

The generator is intentionally kept as a single Python script.

There is no framework, package manager, or build step.

---

## 🔄 Commit Generation Pipeline

Internally, the process looks like this:

```text
Git repository
      │
      ▼
Staged files
      │
      ├───────────────┐
      ▼               ▼
   Git diff      Recent commits
      │               │
      └───────┬───────┘
              ▼
        Context builder
              │
              ▼
         OpenRouter API
              │
              ▼
        Commit title
              │
              ▼
         User review
              │
              ▼
        OpenRouter API
              │
              ▼
       Commit description
              │
              ▼
         User review
              │
              ▼
          git commit
```

The final commit is created locally by Git. The AI only generates the text.

---

## 🔐 Privacy

The tool sends the following repository information to the configured OpenRouter model:

- Staged file names
- Staged diff
- Recent commit subjects

The tool does **not** send your entire repository automatically.

Only the information included in the generated prompt is sent to OpenRouter.

Be careful when staging files containing secrets, credentials, private keys, or other sensitive information.

---

## ⚠️ Limitations

### AI-generated messages are not guaranteed to be perfect

The model can misunderstand complicated changes or choose a less-than-ideal commit type.

Always review the generated title and description before committing.

### Large diffs are truncated

Very large staged diffs are limited before being sent to the model.

This keeps API requests from becoming unnecessarily large, but means the model may not see every line of an extremely large change.

### The tool requires staged changes

Running:

```bash
git aicommit
```

without staged changes will stop with:

```text
There are no staged changes.
```

Stage your changes first:

```bash
git add .
```

---

## 🪝 Git Hook

This project **does not require a Git hook**.

Current implementation handles the entire workflow directly through:

```bash
git aicommit
```

This is intentional.

The AI workflow needs interactive steps for:

- title confirmation
- title editing
- description confirmation
- description editing
- skipping the description

A standalone Git command provides much cleaner control over that workflow than `prepare-commit-msg`.

---

## 🛠️ Technologies

- Python
- Git
- OpenRouter API
- Conventional Commits
- Python `urllib`
- Python `subprocess`
- Python `json`

No external Python dependencies are required.

---

## 📄 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for the complete license text.

---

## ⭐ Support

If you find this useful, consider giving the repository a ⭐ on GitHub.

Made with ❤️ by **RealUnfazed**.
