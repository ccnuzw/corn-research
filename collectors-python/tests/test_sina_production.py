"""Offline fixtures are synthetic test inputs, never production market data."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.sina_production import SinaProductionCollector, SinaSourceError

ARTICLE = '''<h1 class="main-title">2026年10月22日玉米豆粕市场信息分享</h1>
<meta property="article:published_time" content="2026-10-22T06:00:00+08:00">
<div id="artibody"><table><tr><td></td><td></td></tr>
<tr><td>深加工企业</td><td>（元/吨）</td></tr>
<tr><td>测试企业甲</td><td>2,190</td></tr><tr><td>测试企业乙14水</td><td>2100</td></tr></table>
<table><tr><td>豆粕</td><td>元/吨</td></tr><tr><td>测试甲</td><td>3200</td></tr></table></div>'''
URL = 'https://finance.sina.com.cn/money/future/wemedia/2026-10-22/doc-test.shtml'
PAGE = '<a href="' + URL + '">2026年10月22日玉米豆粕市场信息分享</a>'
QUOTE = 'var hq_str_nf_C0="玉米连续,113000,2189,2208,2184,0,2205,2206,2206,0,2190,817,146,1254538,533846,连,玉米,2026-10-22,1";'


class TestSinaCollector(unittest.TestCase):
    def setUp(self):
        self.sleep = Mock()
        self.opener = Mock()
        self.collector = SinaProductionCollector(opener=self.opener, sleep=self.sleep, uniform=lambda a,b: 2)

    def test_parse_date(self):
        for text in ('2026年10月22日', '2026-10-22', '2026/10/22'):
            self.assertEqual(self.collector._parse_date(text), '2026-10-22')
        for text in ('2026-02-30', '10月22日', '2026-10-22 extra'):
            with self.assertRaises(ValueError): self.collector._parse_date(text)

    def test_parse_number(self):
        self.assertEqual(self.collector._parse_number('2,190元/吨'), 2190)
        self.assertEqual(self.collector._parse_number(' 2100.5 '), 2100.5)
        for text in ('--', 'NaN', '0', '-1', '2100-2200', '2100万吨', '2,19'):
            with self.assertRaises(ValueError): self.collector._parse_number(text)

    def test_spot_only_corn_table(self):
        rows = self.collector._parse_spot(ARTICLE, URL)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].value, 2190)
        self.assertEqual(rows[1].metadata['enterprise'], '测试企业乙14水')
        self.assertTrue(all(r.business_date == '2026-10-22' and r.metadata['is_mock'] is False for r in rows))
        self.assertEqual(rows[0].published_at.utcoffset().total_seconds(), 28800)

    def test_missing_report_date_not_replaced_with_today(self):
        self.assertEqual(self.collector._parse_spot(ARTICLE.replace('2026年10月22日', ''), URL), [])

    def test_invalid_or_duplicate_spot_row_fails(self):
        for html in (ARTICLE.replace('2,190', '--'), ARTICLE.replace('测试企业乙14水', '测试企业甲'),
                     ARTICLE.replace('<td>2,190</td>', '<td>2190</td><td>extra</td>')):
            with self.assertRaises(SinaSourceError): self.collector._parse_spot(html, URL)

    def test_futures_field_mapping(self):
        row = self.collector._parse_futures(QUOTE, 'https://hq.sinajs.cn/list=nf_C0')[0]
        self.assertEqual(row.value, 2206)
        self.assertEqual(row.metadata['quote_at'], '2026-10-22T11:30:00+08:00')
        self.assertTrue(row.metadata['continuous'])
        self.assertEqual(row.metadata['topic_name'], 'corn_futures_price')

    def test_futures_invalid_response(self):
        for quote in ('', QUOTE.replace('玉米,', '豆粕,'), QUOTE.replace('113000', '253000')):
            with self.assertRaises((SinaSourceError, ValueError)):
                self.collector._parse_futures(quote, 'https://hq.sinajs.cn/')

    def test_collect_and_limit(self):
        for limit in (1, 2, 100):
            self.collector._request = Mock(side_effect=[PAGE, ARTICLE, QUOTE])
            rows = self.collector.collect(max_items=limit)
            self.assertEqual(len(rows), min(limit, 3))
            self.assertEqual(rows[0].indicator, '玉米期货价格')
        for limit in (0, -1, True):
            with self.assertRaises(ValueError): self.collector.collect(max_items=limit)

    def test_missing_table_never_returns_mock(self):
        self.collector._request = Mock(return_value='<html>No corn table</html>')
        with self.assertRaises(SinaSourceError): self.collector.collect()

    def test_newest_report_selected_and_external_link_ignored(self):
        old = PAGE.replace('2026-10-22', '2026-10-21').replace('2026年10月22日', '2026年10月21日')
        bad = PAGE.replace('finance.sina.com.cn', 'evil.invalid')
        self.collector._request = Mock(side_effect=[old+bad+PAGE, ARTICLE, QUOTE])
        self.collector.collect()
        self.assertEqual(self.collector._request.call_args_list[1].args[0], URL)

    def test_retry_pacing_headers_and_encoding(self):
        self.opener.side_effect = [URLError('test network failure')] * 3 + [io.BytesIO('玉米'.encode('gb18030'))]
        self.assertEqual(self.collector._request(URL), '玉米')
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [2,1,2,2,2,4,2])
        self.assertEqual(self.opener.call_count, 4)
        requests = [c.args[0] for c in self.opener.call_args_list]
        self.assertEqual(requests[0].get_header('Referer'), self.collector.site_url)
        self.assertNotEqual(requests[0].get_header('User-agent'), requests[1].get_header('User-agent'))

    def test_retry_exhaustion(self):
        self.opener.side_effect = URLError('test unreachable')
        with self.assertRaises(URLError): self.collector._request(URL)
        self.assertEqual(self.opener.call_count, 4)

    def test_http_status_retry_policy(self):
        for status, attempts in ((403,1),(404,1),(408,4),(429,4),(500,4)):
            self.opener.reset_mock()
            self.opener.side_effect = HTTPError(URL, status, 'test', {}, None)
            with self.assertRaises(HTTPError): self.collector._request(URL)
            self.assertEqual(self.opener.call_count, attempts)

    def test_contract_config_validation(self):
        for symbols in ([], ['nf_M0'], ['nf_C0&evil=1']):
            with self.assertRaises(ValueError): SinaProductionCollector(symbols=symbols)

    def test_only_desktop_user_agents_on_every_request(self):
        # Mobile Sina channel is a CBOT SPA, not the domestic corn news page.
        for _ in range(6):
            self.opener.return_value = io.BytesIO(PAGE.encode())
            self.collector._request(self.collector.site_url)
        for call in self.opener.call_args_list:
            ua = call.args[0].get_header('User-agent')
            self.assertFalse(any(word in ua for word in ('iPhone', 'Mobile', 'Android')), ua)

    def test_index_fallback_when_channel_returns_mobile_shell(self):
        shell = '<title>CBOT-玉米(C)-期货行情</title><div id="app"></div>'
        self.collector._request = Mock(side_effect=[shell, PAGE, ARTICLE, QUOTE])
        rows = self.collector.collect()
        self.assertEqual(len(rows), 3)
        self.assertEqual(self.collector._request.call_args_list[1].args[0],
                         'https://finance.sina.com.cn/futuremarket/')

    def test_alternate_article_containers_headers_and_title(self):
        for body in ('<article>', '<div id="article_content">', '<div class="article-content">'):
            html = ARTICLE.replace('<div id="artibody">', body)
            if body == '<article>':
                html = html.replace('</table></div>', '</table></article>')
            html = html.replace('class="main-title"', '').replace('深加工企业', '深 加 工 厂 家')
            html = html.replace('元/吨', '元／吨')
            self.assertEqual(len(self.collector._parse_spot(html, URL)), 2)

    def test_link_title_attribute_and_abbreviated_link_date(self):
        page = '<a href="' + URL + '" title="玉米现货市场信息">10月22日价格...</a>'
        self.assertEqual(self.collector._discover_articles(page), [URL])

    def test_broken_candidate_does_not_hide_next_valid_report(self):
        other = PAGE.replace('doc-test', 'doc-other')
        self.collector._request = Mock(side_effect=[PAGE+other, ARTICLE.replace('2,190', '--'), ARTICLE, QUOTE])
        self.assertEqual(len(self.collector.collect()), 3)

    def test_exhausted_candidates_include_diagnostics(self):
        self.collector._request = Mock(side_effect=[PAGE, '<html>unmatched response</html>'])
        with self.assertLogs('collectors.sina_production', level='WARNING') as logs:
            with self.assertRaises(SinaSourceError) as error:
                self.collector.collect()
        self.assertIn('candidates=1; attempted=1', str(error.exception))
        self.assertIn(URL, str(error.exception))
        self.assertIn('missing_report_date', '\n'.join(logs.output))

    def test_invalid_publication_metadata_keeps_explicit_business_date(self):
        html = ARTICLE.replace('2026-10-22T06:00:00+08:00', 'not-a-timestamp')
        rows = self.collector._parse_spot(html, URL)
        self.assertEqual(rows[0].business_date, '2026-10-22')
        self.assertIsNone(rows[0].published_at)


if __name__ == '__main__':
    unittest.main()
