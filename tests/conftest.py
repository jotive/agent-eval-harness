import pytest

from app.core.judge import Judge


class StubCompletions:
    def __init__(self, contents, error=None):
        self.contents = list(contents)
        self.error = error
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        content = self.contents[min(self.calls - 1, len(self.contents) - 1)]
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        usage = type("Usage", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("Response", (), {"choices": [choice], "usage": usage})()


class StubClient:
    def __init__(self, contents=(), error=None):
        self.completions = StubCompletions(contents, error)
        self.chat = type("Chat", (), {"completions": self.completions})()


@pytest.fixture
def make_judge(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _make(contents=(), error=None, **kwargs):
        judge = Judge(**kwargs)
        judge._client = StubClient(contents, error)
        return judge

    return _make
