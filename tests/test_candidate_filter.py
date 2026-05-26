from xhs_agent.crawl.candidate_filter import is_candidate_post, hard_excluded, has_recall_signal


def test_candidate_filter_accepts_backend_interview_titles():
    assert is_candidate_post("PDD服务端一面", "项目怎么上线\nnginx和springboot如何通信")


def test_candidate_filter_accepts_ai_agent_interview_titles():
    assert is_candidate_post("AI应用开发一面", "RAG召回链路\nAgent tool calling")


def test_candidate_filter_rejects_excluded_targets():
    assert is_candidate_post("Golang 面试 一面", "项目介绍") is False
    assert is_candidate_post("Golang一面", "项目介绍") is False
    assert is_candidate_post("C++面经", "手撕题") is False


def test_candidate_filter_no_false_positive_on_go_substring():
    # "mongodb" 中包含 "go" 不应触发误杀
    assert hard_excluded("后端面经", "MongoDB 索引原理") is False


def test_candidate_filter_does_not_recall_on_social_recruiting_alone():
    assert has_recall_signal("社招记录", "普通分享") is False
