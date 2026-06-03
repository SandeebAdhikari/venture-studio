"""Shared RSS test fixtures."""

def sample_rss_xml(*, duplicate_guid: bool = False) -> str:
    duplicate_item = """
    <item>
      <title>Duplicate headline</title>
      <link>https://example.com/article/1</link>
      <description>Duplicate body text.</description>
      <guid>article-1</guid>
    </item>
    """ if duplicate_guid else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Business Signals</title>
    <item>
      <title>Startup funding slowdown</title>
      <link>https://example.com/article/1</link>
      <description>Industry signals show tightening capital markets.</description>
      <guid>article-1</guid>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Construction labor shortage</title>
      <link>https://example.com/article/2</link>
      <description>Contractors report rising costs and project delays.</description>
      <guid>article-2</guid>
    </item>
    {duplicate_item}
  </channel>
</rss>"""
