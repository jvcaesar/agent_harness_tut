"""ch-01 — Model only.

Capability (persists): a single send() returns the model's reply, made through a
swappable Provider seam.

ch-01 is stateless — the agent forgets across turns. That is a *limitation*, not a
capability, so we don't pin it with a test here: ch-02 lifts it by adding history,
and its test guards the new capability. Tests that guard capabilities persist;
tests that pin a limitation retire when a later chapter removes it.

The model is patched here so the test is deterministic and offline; the real model
run lives in ``uv run accept ch-01``.
"""

from unittest.mock import patch

import harness.agent as agent_mod
from model import LLMResponse, Provider, lmstudio, ollama, openrouter
from model.openai_compatible import complete_openai


def test_send_returns_model_content():
    with patch.object(agent_mod, "chat", return_value=LLMResponse(content="hello there")) as m:
        out = agent_mod.Agent().send("hi")
    assert out == "hello there"
    assert m.call_count == 1


def test_should_exit_checks_common_shutdown_commands():
    assert agent_mod.should_exit("exit")
    assert agent_mod.should_exit("QUIT")
    assert agent_mod.should_exit("stop")
    assert agent_mod.should_exit("bye!")
    assert not agent_mod.should_exit("hello there")


# --- provider seam -----------------------------------------------------------
def test_presets_configure_endpoints():
    assert openrouter("m", "k").base_url == "https://openrouter.ai/api/v1"
    assert ollama("m").base_url == "http://localhost:11434/v1"
    assert lmstudio().model  # has a default model


def test_agent_routes_through_provider():
    seen = {}

    def fake_chat(messages, **kwargs):
        seen["provider"] = kwargs.get("provider")
        return LLMResponse(content="ok")

    p = Provider(base_url="http://example/v1", model="m", api_key="k")
    with patch.object(agent_mod, "chat", side_effect=fake_chat):
        agent_mod.Agent(provider=p).send("hi")

    assert seen["provider"] is p  # nothing above changed — only the seam


def test_complete_openai_adds_http_scheme_when_missing():
    provider = Provider(base_url="localhost:1234/v1", model="m", api_key="k")
    with patch("model.openai_compatible.httpx.post") as post:
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]
        }

        complete_openai(provider, [{"role": "user", "content": "hi"}])

    assert post.call_args.args[0] == "http://localhost:1234/v1/chat/completions"


def test_from_env_strips_matching_quotes_from_dotenv_values(monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text('LLM_BASE_URL="http://localhost:1234/v1"\nLLM_MODEL="m"\n')
    monkeypatch.chdir(tmp_path)

    provider = Provider.from_env()

    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "m"


def test_from_env_finds_parent_dotenv(monkeypatch, tmp_path):
    project_dir = tmp_path / "project"
    nested_dir = project_dir / "nested"
    nested_dir.mkdir(parents=True)
    (project_dir / ".env").write_text('LLM_BASE_URL="http://example/v1"\nLLM_MODEL="m"\n')
    monkeypatch.chdir(nested_dir)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = Provider.from_env()

    assert provider.base_url == "http://example/v1"
    assert provider.model == "m"
