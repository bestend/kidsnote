import unittest

from kd.cli import (
    AppConfig,
    ChildConfig,
    build_album_params,
    build_album_request_configs,
    format_album_fetch_stats,
    merge_album_results,
    merge_child_configs,
)


class ChildConfigTests(unittest.TestCase):
    def test_merge_preserves_non_zero_center_and_cls(self):
        merged = merge_child_configs(
            [
                ChildConfig(child_id=1001, center=2001, cls=3001, name=""),
                ChildConfig(child_id=1001, center=0, cls=0, name=""),
            ]
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].child_id, 1001)
        self.assertEqual(merged[0].center, 2001)
        self.assertEqual(merged[0].cls, 3001)

    def test_build_album_params_omits_zero_center_and_cls(self):
        params = build_album_params(ChildConfig(child_id=1001, center=0, cls=0))

        self.assertEqual(
            params,
            {
                "tz": "Asia/Seoul",
                "page_size": 10000,
                "child": 1001,
            },
        )

    def test_build_album_request_configs_includes_current_and_past(self):
        configs = build_album_request_configs(
            ChildConfig(child_id=1001, center=2001, cls=3001)
        )

        self.assertEqual(
            configs,
            [
                {
                    "tz": "Asia/Seoul",
                    "page_size": 10000,
                    "child": 1001,
                    "center": 2001,
                    "cls": 3001,
                },
                {
                    "tz": "Asia/Seoul",
                    "page_size": 10000,
                    "child": 1001,
                },
            ],
        )

    def test_merge_album_results_deduplicates_entries(self):
        merged = merge_album_results(
            [
                {
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [{"id": 1, "created": "2026-03-27T00:00:00"}],
                },
                {
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {"id": 1, "created": "2026-03-27T00:00:00"},
                        {"id": 2, "created": "2026-03-26T00:00:00"},
                    ],
                },
            ]
        )

        self.assertEqual(merged["count"], 2)
        self.assertEqual([entry["id"] for entry in merged["results"]], [1, 2])

    def test_format_album_fetch_stats_includes_breakdown(self):
        stats = format_album_fetch_stats(
            current_count=77,
            past_count=630,
            merged_count=630,
        )

        self.assertEqual(stats, "현재 77개, 추억 630개, 합계 630개")

    def test_app_config_load_merges_duplicate_children(self):
        config = AppConfig.from_dict(
            {
                "download_dir": "/tmp/kidsnote",
                "children": [
                    {"child_id": 1001, "center": 0, "cls": 0, "name": ""},
                    {
                        "child_id": 1001,
                        "center": 2001,
                        "cls": 3001,
                        "name": "테스트아이",
                    },
                ],
            }
        )

        self.assertEqual(len(config.children), 1)
        self.assertEqual(config.children[0].center, 2001)
        self.assertEqual(config.children[0].cls, 3001)
        self.assertEqual(config.children[0].name, "테스트아이")


if __name__ == "__main__":
    unittest.main()
