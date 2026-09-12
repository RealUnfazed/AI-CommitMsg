# 🤖 AI Conventional Commit

An AI-powered Git commit assistant that analyzes your **staged changes** and generates a Conventional Commit title and description using OpenRouter.

Instead of staring at a diff trying to figure out what to write, run:

```bash
git add .
git aicommit
```

The AI generates the commit message, lets you review or edit it, and then creates the commit for you.

No Git editor. No Vim. No commit-message template.

---

## ✨ Features

- 🤖 AI-generated Conventional Commit titles
- 📝 AI-generated commit descriptions
- ✏️ Edit the title before committing
- ✏️ Edit the description before committing
- ⏭️ Choose title-only commits
- 🔍 Analyzes staged files and the actual staged diff
- 🧠 Uses recent commit history for context
- 📏 Keeps generated commit titles concise
- 🧩 Supports Conventional Commit types, scopes, and breaking changes
- ⚡ Runs directly through a simple Git alias
- 🌐 Uses OpenRouter's API
- 🔄 Supports fallback models when the configured model is unavailable
- 🎯 Supports choosing a model for a single command
- 🛠 No framework or heavy dependencies
- 🚫 No Git hook required

---

## 🚀 How It Works

When you run:

```bash
git aicommit
```

the generator first asks whether you want a **title only** or a **title + description** commit.

### Title only

```text
git aicommit
       │
       ▼
Analyze staged changes
       │
       ▼
Generate title
       │
  ┌────┼────┐
  ▼    ▼    ▼
 Yes  Edit  No
  │    │    │
  │    ▼    │
  │ Review  │
  │ again   │
  └────┬────┘
       │
       ▼
   git commit
```

### Title + description

The title is generated first.

While you review or edit the title, the description is generated **in the background**. This means the description can already be ready by the time you finish reviewing the title.

```text
                 git aicommit
                      │
                      ▼
             Analyze staged changes
                      │
                      ▼
                Generate title
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
        Review title     Generate description
              │             in background
              │                │
       ┌──────┼──────┐         │
       ▼      ▼      ▼         │
      Yes    Edit    No        │
       │      │      │         │
       │      ▼      │         │
       │   Review    │         │
       │    again    │         │
       └──────┬──────┘         │
              │                │
              └───────┬────────┘
                      ▼
             Review description
                      │
               ┌──────┼──────┐
               ▼      ▼      ▼
              Yes    Edit    No
               │      │      │
               │      ▼      │
               │   Review    │
               │    again    │
               └──────┬──────┘
                      │
                      ▼
                 git commit
```

---

## 📝 Example

When starting the command, you'll choose the type of commit you want:

```text
What would you like to generate?

[1] Title only
[2] Title + description
[N] Cancel

Choose [1/2/n]:
```

For a title-only commit:

```text
Generating AI commit title...

Generated commit title:

  feat: add AI commit generation

[Y] Yes
[E] Edit
[N] Cancel

Choose [Y/e/n]: y


Committing...

[master 4c91a2f] feat: add AI commit generation
```

For a title + description commit:

```text
Generating AI commit title...

Generated commit title:

  feat: add AI commit generation

Generating AI commit description in background...

[Y] Yes
[E] Edit
[N] Cancel

Choose [Y/e/n]: y
```

If you choose to skip the description, the commit is created using the title only:

```text
feat: add AI commit generation
```

---

## 🧠 What the AI Sees

The generator builds its context from your repository instead of asking the model to blindly guess what changed.

It provides:

### 📂 Staged files

For example:

```text
M       README.md
A       ai_commit.py
```

### 🔀 Staged diff

The actual output of:

```bash
git diff --cached
```

This is the primary source of truth for the generated commit.

### 📜 Recent commits

Recent commit subjects are also provided so the generated message can better match the existing style of the repository.

The diff is limited to a configurable size before being sent to the API to avoid unnecessarily large requests.

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

No Python packages are required.

### 1. Get the project

Clone the repository or download it to your computer.

```bash
git clone https://github.com/RealUnfazed/AI-CommitMsg.git
cd AI-CommitMsg
```

### 2. Create your `.env`

Copy the provided example configuration:

#### PowerShell

```powershell
Copy-Item .env.example .env
```

#### CMD

```cmd
copy .env.example .env
```

### 3. Add your OpenRouter API key

Open `.env` and set your API key:

```env
OPENROUTER_API_KEY=your-api-key
```

You can also change the default model and other settings in this file.

### 4. Configure the Git alias

Tell Git where `ai_commit.py` is located:

```powershell
git config --global alias.aicommit '!python "C:/path/to/ai_commit.py"'
```

For example:

```powershell
git config --global alias.aicommit '!python "C:/Users/Unfazed/Documents/Python/AI-CommitMsg/ai_commit.py"'
```

### 5. Start using it

Go to any Git repository, stage your changes, and run:

```bash
git add .
git aicommit
```

That's it.

---

## 🔑 Configuration

The available configuration options are provided in `.env.example`.

A typical `.env` looks like:

```env
# OpenRouter
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY

# Default model
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free

# Comma-separated fallback models
OPENROUTER_FALLBACK_MODELS=

# OpenRouter API
OPENROUTER_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_HTTP_REFERER=https://github.com/RealUnfazed
OPENROUTER_TITLE=AI Conventional Commit Generator

# Generation
MAX_DIFF_CHARS=30000
MAX_HISTORY_COMMITS=30
MAX_TOKENS=180
REQUEST_TIMEOUT=120
TEMPERATURE=0
```

Most users only need to configure:

```env
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=your-model
```

The other options can be left at their defaults.

---

## 🔄 Fallback Models

You can configure additional models in `.env`:

```env
OPENROUTER_FALLBACK_MODELS=model-one,model-two,model-three
```

For example:

```env
OPENROUTER_MODEL=primary/model
OPENROUTER_FALLBACK_MODELS=fallback/model-one,fallback/model-two
```

If the primary model is temporarily unavailable, overloaded, or rate-limited, the generator can try the configured fallback models.

This can be especially useful when using free models.

---

## 🎯 Choose a Model for One Commit

You can override the default model for a single run:

```bash
git aicommit --model "another/model"
```

For example:

```bash
git aicommit --model "nvidia/nemotron-3-ultra-550b-a55b:free"
```

This only affects that command and does not change your `.env`.

---

## 🛠️ Git Alias

The project is designed to be used through:

```bash
git aicommit
```

If you need to change the alias later, remove the existing one:

```powershell
git config --global --unset alias.aicommit
```

Then configure it again:

```powershell
git config --global alias.aicommit '!python "C:/path/to/ai_commit.py"'
```

You can check the current alias with:

```powershell
git config --global --get alias.aicommit
```

---

## 📦 Usage

Stage the changes you want included:

```bash
git add .
```

Then run:

```bash
git aicommit
```

The generator will ask:

```text
What would you like to generate?

[1] Title only
[2] Title + description
[N] Cancel

Choose [1/2/n]:
```

### Title only

Choose this when you only want a Conventional Commit title:

```text
feat: add user authentication
```

### Title + description

Choose this when you want both:

```text
feat: add user authentication

Add authentication support for user accounts and
protect authenticated routes.
```

Normal Git commits still work normally:

```bash
git commit
```

But `git aicommit` is the command that invokes the AI generator.

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

If you selected the title + description workflow, you can choose:

```text
[N] No description
```

The commit is still created using the title only:

```text
feat: add AI commit generation
```

---

## 🧩 Project Structure

```text
AI-CommitMsg/
│
├── ai_commit.py
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

The generator is intentionally kept as a single Python script.

There is no framework, package manager, or build step.

## 🔐 Privacy

The tool sends the following repository information to the configured OpenRouter model:

- Staged file names
- Staged diff
- Recent commit subjects

The tool does **not** send your entire repository automatically.

Only the information included in the generated prompt is sent to OpenRouter.

Be careful when staging files containing sensitive information such as:

- API keys
- Passwords
- Credentials
- Private keys
- Tokens

---

## ⚠️ Limitations

### AI-generated messages are not guaranteed to be perfect

The model can misunderstand complicated changes or choose a less-than-ideal commit type.

Always review the generated title and description before committing.

### Large diffs are truncated

Very large staged diffs are limited before being sent to the model.

This keeps API requests from becoming unnecessarily large, but means the model may not see every line of an extremely large change.

The limit can be configured with:

```env
MAX_DIFF_CHARS=30000
```

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

### Model availability can vary

OpenRouter models, especially free models, can occasionally be unavailable, overloaded, or rate-limited.

Configure fallback models if you want additional options.

---

## 🪝 Git Hook

This project **does not require a Git hook**.

The entire workflow is handled directly through:

```bash
git aicommit
```

This is intentional.

The AI workflow needs interactive steps for:

- Choosing title-only or title + description
- Title confirmation
- Title editing
- Description confirmation
- Description editing
- Skipping the description

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
