from xhs_agent.crawl.html_extract import extract_post_detail


HTML = """
<html>
  <body>
    <div class="title">PDD服务端一面</div>
    <div class="content">
      <p>项目怎么上线，怎么部署</p>
      <p>nginx和springboot如何通信</p>
      <p>手撕：数组按k分组</p>
    </div>
    <img class="note-image" src="https://cdn.example.com/1.png" />
  </body>
</html>
"""


def test_extract_post_detail_reads_title_body_and_images():
    post = extract_post_detail(HTML)

    assert post.title == "PDD服务端一面"
    assert post.body_text == "项目怎么上线，怎么部署\nnginx和springboot如何通信\n手撕：数组按k分组"
    assert post.image_urls == ["https://cdn.example.com/1.png"]
