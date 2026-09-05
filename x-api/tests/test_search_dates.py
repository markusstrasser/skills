"""Offline regression checks for the shared X search date-window interface."""
import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/search.py'
spec = importlib.util.spec_from_file_location('x_search_dates', SOURCE)
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)
START = '2026-06-05T00:00:00Z'
END = '2026-08-01T00:00:00Z'


class DateSearchTest(unittest.TestCase):
    def test_window_and_cap_survive_pagination(self):
        pages = [
            {'data': [{'id': '1'}], 'meta': {'next_token': 'page2'}},
            {'data': [{'id': '2'}], 'meta': {'next_token': 'page3'}},
        ]
        tally = search.CostTally()
        with patch.object(search, '_get', side_effect=pages) as request, patch.object(search.time, 'sleep'):
            rows = search.search_all('immigration', 2, 10, tally, start_time=START, end_time=END)
        self.assertEqual([r['id'] for r in rows], ['1', '2'])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(tally.tweet_reads, 2)
        self.assertEqual(tally.usd, 0.01)
        for call in request.call_args_list:
            self.assertEqual(call.args[1]['start_time'], START)
            self.assertEqual(call.args[1]['end_time'], END)
            self.assertEqual(call.args[1]['max_results'], 10)
        self.assertEqual(request.call_args_list[1].args[1]['next_token'], 'page2')

    def test_absent_and_single_bounds(self):
        for kwargs in ({}, {'start_time': START}, {'end_time': END}):
            with self.subTest(kwargs=kwargs), patch.object(search, '_get', return_value={}) as request:
                search.search_all('immigration', 1, 10, search.CostTally(), **kwargs)
                for name in ('start_time', 'end_time'):
                    self.assertEqual(request.call_args.args[1].get(name), kwargs.get(name))

    def test_invalid_bounds_make_no_paid_call(self):
        for start, end in (
            (END, START), (START, START), ('2026-02-30T00:00:00Z', END),
            ('2026-06-05', END), ('2026-06-05T00:00:00', END),
            ('2026-6-05T00:00:00Z', END),
            ('2999-01-01T00:00:00Z', None), (None, '2999-01-01T00:00:00Z'),
        ):
            with self.subTest(start=start, end=end), patch.object(search, '_get') as request:
                with self.assertRaises(ValueError):
                    search.search_all('immigration', 1, 10, search.CostTally(), start_time=start, end_time=end)
                request.assert_not_called()

    def test_cli_rejects_before_network_or_ledger(self):
        argv = ['search.py', 'query', 'immigration', '--start-time', END, '--end-time', START]
        with patch.object(sys, 'argv', argv), patch.object(search, '_get') as request, \
             patch.object(search, 'log_cost') as ledger, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                search.main()
            self.assertEqual(error.exception.code, 2)
            request.assert_not_called()
            ledger.assert_not_called()

    def test_cli_passes_bounds_and_preserves_retweet_and_ledger_behavior(self):
        argv = ['search.py', 'query', 'immigration', '--start-time', START, '--end-time', END,
                '--max', '40', '--pages', '1', '--label', 'offline_date_test']
        with patch.object(sys, 'argv', argv), patch.object(search, 'search_all', return_value=[]) as fetch, \
             patch.object(search, 'log_cost') as ledger, contextlib.redirect_stdout(io.StringIO()):
            search.main()
            self.assertEqual(fetch.call_args.args[:3], ('immigration -is:retweet', 1, 40))
            self.assertEqual(fetch.call_args.kwargs, {'start_time': START, 'end_time': END})
            self.assertEqual(ledger.call_args.args[1], 'offline_date_test')


if __name__ == '__main__':
    unittest.main(verbosity=2)
