from xhs_agent.extract.line_questions import split_to_candidate_lines, should_run_ocr


def test_split_to_candidate_lines_handles_numbered_and_plain_lines():
    body = """PDD服务端一面

1. 项目怎么上线，怎么部署
2. nginx 和 springboot 如何通信
手撕：数组按 k 分组
MySQL 索引原理
字数 1024
点赞 32"""

    result = split_to_candidate_lines(body)
    assert "项目怎么上线，怎么部署" in result
    assert "nginx 和 springboot 如何通信" in result
    assert "手撕：数组按 k 分组" in result
    assert "MySQL 索引原理" in result
    # 元数据行不应出现在候选行中
    assert not any("字数" in line for line in result)
    assert not any("点赞" in line for line in result)


def test_split_to_candidate_lines_filters_too_short_and_too_long():
    body = "ABC\nRedis\n非常" + "长" * 300
    result = split_to_candidate_lines(body)
    assert "ABC" not in result  # 3 字符太短
    assert "Redis" in result  # 5 字符够长
    assert not any(len(line) > 200 for line in result)


def test_should_run_ocr_only_when_no_candidate_lines():
    assert should_run_ocr(["项目怎么上线"]) is False
    assert should_run_ocr([]) is True
