"""ChatGPT adapter tests. Synthetic fixture only — no real export, no network.

Run from the distill root: python3 -m signal_action.tests.test_chatgpt
"""
import os

from signal_action.capture.adapters.chatgpt import (
    ChatGPTAdapter,
    from_gemini_takeout,
    parse_conversations,
    parse_file,
    records_from_turns,
)

FIX = os.path.join(os.path.dirname(__file__), "fixtures",
                   "synth-chatgpt.json")


def test_roles_and_multipart():
    recs = parse_file(FIX)
    by_role = {}
    for r in recs:
        by_role.setdefault(r.role, []).append(r)
    assert set(by_role) == {"user", "assistant", "system"}, by_role.keys()
    # multi-part assistant content joined
    a = by_role["assistant"][0]
    assert a.content == "How about hiking on Saturday?", a.content
    # non-string part skipped, strings joined
    u2 = [r for r in by_role["user"] if "see you then" in r.content][0]
    assert u2.content == "Sounds good, see you then", u2.content
    for r in recs:
        assert r.platform == "chatgpt"
        assert r.stream == "messages"
    print("roles + multipart: OK")


def test_chronological_order_and_ids():
    recs = parse_file(FIX)
    conv_a = [r for r in recs if r.session_id == "conv-alpha"]
    # n4 (create_time ...000.5) sorts before n1 (...001.0) despite mapping order
    assert conv_a[0].content.startswith("Sounds good"), conv_a[0].content
    assert conv_a[0].message_id == "msg-u2"
    assert conv_a[1].message_id == "msg-u1"
    assert conv_a[0].ts.startswith("2024-10-04"), conv_a[0].ts
    assert conv_a[1].metadata["conversation_title"] == "Weekend plans"
    print("chronological order + ids: OK")


def test_missing_fields_tolerated():
    recs = parse_file(FIX)
    # conv-beta: mapping not a dict -> no records, no crash
    assert not [r for r in recs if r.session_id == "conv-beta"]
    # third conv: no id -> conv-<index> fallback; empty parts -> skipped
    conv2 = [r for r in recs if r.session_id == "conv-2"]
    assert len(conv2) == 1 and conv2[0].content == "hello"
    assert conv2[0].message_id == "empty-parts"  # node id fallback
    assert conv2[0].ts.startswith("2024-10-04")  # real create_time -> ISO
    # unknown role 'narrator' skipped, root null-message skipped
    assert not [r for r in recs if "unknown role" in r.content]
    print("missing fields tolerated: OK")


def test_non_list_payload():
    assert parse_conversations({"nope": 1}) == []
    assert parse_conversations(None) == []
    # null create_time -> empty ts, no crash
    recs = parse_conversations([{"id": "c", "title": "t", "mapping": {
        "n": {"children": [], "id": "n", "message": {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["hi"]},
            "create_time": None, "id": "m"}, "parent": None}}}])
    assert len(recs) == 1 and recs[0].ts == ""
    print("non-list payload: OK")


def test_adapter_interface():
    ad = ChatGPTAdapter()
    recs = list(ad.iter_records(FIX))
    assert recs and all(r.platform == "chatgpt" for r in recs)
    assert "conversations.json" in ad.describe_source()
    print("adapter interface: OK")


def test_records_from_turns_gemini_path():
    turns = [
        {"role": "user", "text": "summarize this", "ts": 1728000000.0},
        {"role": "model", "text": "done", "ts": 1728000001.0},
        {"role": "weird", "text": "skipped", "ts": 0},
    ]
    recs = records_from_turns(turns, "gemini", "g-1")
    assert [r.role for r in recs] == ["user", "assistant"]
    assert all(r.platform == "gemini" for r in recs)
    assert recs[0].ts.startswith("2024-10-04")
    print("records_from_turns (gemini path): OK")


def test_from_gemini_takeout_best_effort():
    data = [{"id": "g1", "title": "t",
             "turns": [{"role": "user", "text": "hi", "ts": 1.0}]}]
    recs = from_gemini_takeout(data)
    assert len(recs) == 1 and recs[0].platform == "gemini"
    assert from_gemini_takeout({"no": "turns"}) == []
    assert from_gemini_takeout([{"role": "user", "text": "solo", "ts": 1.0}])
    print("from_gemini_takeout best-effort: OK")


if __name__ == "__main__":
    test_roles_and_multipart()
    test_chronological_order_and_ids()
    test_missing_fields_tolerated()
    test_non_list_payload()
    test_adapter_interface()
    test_records_from_turns_gemini_path()
    test_from_gemini_takeout_best_effort()
    print("\nALL CHATGPT ADAPTER TESTS PASSED")
