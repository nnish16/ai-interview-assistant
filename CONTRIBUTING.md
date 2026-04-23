# Contributing to ai-interview-assistant

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/nnish16/ai-interview-assistant.git
cd ai-interview-assistant
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Making Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Commit with a descriptive message: `git commit -m "feat: add new feature"`
5. Push to your fork: `git push origin feat/your-feature`
6. Open a Pull Request

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or correcting tests
- `chore:` — maintenance tasks

## Code Style

- Python: We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting


## Reporting Issues

Use [GitHub Issues](https://github.com/nnish16/ai-interview-assistant/issues) with the provided templates.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
