"""Collector unit tests."""

from unittest.mock import MagicMock, call, patch

import pytest

import osxcollector.osxcollector
import osxcollector.sqlite_utils as sqlite_utils
from osxcollector.osxcollector import Collector, HomeDir, Logger


class TestCollector:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self):
        homedirs = [HomeDir("test", "/Users/test")]
        self.expected_file_info = {
            "md5": "8675309",
            "sha1": "babababa",
            "sha2": "11",
        }
        with (
            patch.object(
                Logger,
                "log_dict",
            ) as self.mock_log_dict,
            patch(
                "osxcollector.osxcollector._get_homedirs",
                autospec=True,
                return_value=homedirs,
            ) as self.mock_get_homedirs,
            patch(
                "osxcollector.collectors.base.get_homedirs",
                autospec=True,
                return_value=homedirs,
            ),
            patch(
                "osxcollector.osxcollector._get_file_info",
                autospec=True,
                return_value=self.expected_file_info,
            ) as self.mock_get_file_info,
            patch(
                "osxcollector.collectors.startup.get_file_info",
                autospec=True,
                return_value=self.expected_file_info,
            ),
            patch(
                "osxcollector.collectors.applications.get_file_info",
                autospec=True,
                return_value=self.expected_file_info,
            ),
            patch(
                "osxcollector.collectors.base.get_file_info",
                autospec=True,
                return_value=self.expected_file_info,
            ),
        ):
            self.collector = Collector()
            yield

    def test_log_items_in_plist(self):
        plist = {
            "system": {
                "name": ["os x"],
            },
            "version": {
                "minor": "3",
            },
        }

        self.collector._log_items_in_plist(plist, "system.name")
        self.mock_log_dict.assert_called_with("os x")

    def _really_expected_file_info(self, expected):
        really_expected = {}
        really_expected.update(expected)
        really_expected.update(self.expected_file_info)
        return really_expected

    def _test_log_launch_agents(self, dir_path, expected):
        expected = self._really_expected_file_info(expected)

        self.collector._log_launch_agents(dir_path)
        self.mock_log_dict.assert_called_with(expected)

    def test_log_launch_agents_just_program_no_arguments(self):
        expected = {
            "label": "com.apple.csuseragent",
            "program": "/System/Library/CoreServices/CSUserAgent",
            "osxcollector_plist": "tests/data/launch_agents/csuseragent/csuseragent.plist",
        }
        self._test_log_launch_agents("tests/data/launch_agents/csuseragent/", expected)

    def test_log_launch_agents_program(self):
        expected = {
            "label": "com.apple.appleseed.seedusaged",
            "program": "/System/Library/CoreServices/Feedback Assistant.app/Contents/Library/LaunchServices/seedusaged",
            "osxcollector_plist": "tests/data/launch_agents/seedusaged/seedusaged.plist",
        }
        self._test_log_launch_agents("tests/data/launch_agents/seedusaged/", expected)

    def test_log_launch_agents_program_and_arguments(self):
        expected = {
            "label": "com.apple.VoiceOver",
            "program": "/System/Library/CoreServices/VoiceOver.app/Contents/MacOS/VoiceOver",
            "arguments": ["launchd", "-s"],
            "osxcollector_plist": "tests/data/launch_agents/voice_over/com.apple.VoiceOver.plist",
        }
        self._test_log_launch_agents("tests/data/launch_agents/voice_over/", expected)

    def test_log_packages_in_dir(self):
        expected = {
            "osxcollector_plist_path": "tests/data/packages/Digital Hub Scripting.osax/Contents/Info.plist",
            "osxcollector_bundle_id": "com.apple.osax.digihub",
        }
        expected = self._really_expected_file_info(expected)

        self.collector._log_packages_in_dir("tests/data/packages/")
        self.mock_log_dict.assert_called_with(expected)

    def test_collect_binary_names_in_path(self):
        expected = ["/usr/bin/ls", "/usr/bin/pwd"]

        with (
            patch(
                "os.walk",
                autospec=True,
                return_value=[
                    ["/usr", ("test",), ("bin/ls", "bin/pwd", "bin/tmp")],
                ],
            ),
            patch(
                "os.path.isfile",
                autospec=True,
                side_effect=[True, True, False, True, True, False],
            ),
            patch(
                "os.access",
                autospec=True,
                side_effect=[True, True, True, True, True, True],
            ),
            patch.dict(
                "os.environ",
                {"PATH": "/usr/bin"},
            ),
        ):
            self.collector._collect_binary_names_in_path()
            self.mock_log_dict.assert_called_once_with(
                {
                    "executable_files": expected,
                }
            )

    def test_log_startup_items(self):
        list_of_files_in_dir = ["StartupParameters.plist"]
        plist = {
            "Provides": ["test_service"],
        }
        with (
            patch(
                "os.path.isdir",
                autospec=True,
                return_value=True,
            ),
            patch(
                "osxcollector.collectors.startup.listdir",
                autospec=True,
                return_value=list_of_files_in_dir,
            ),
            patch.object(
                Collector,
                "_read_plist",
                autospec=True,
                return_value=plist,
            ),
        ):
            self.collector._log_startup_items("test_dir")
            self.mock_log_dict.assert_called_with(self.expected_file_info)

    def test_log_user_login_items(self):
        plist_path = "/Users/test/Library/Preferences/com.apple.loginitems.plist"
        login_item = {
            "Name": "test-login-item",
        }
        plist = {
            "SessionItems": {
                "CustomListItems": [login_item],
            },
        }
        with patch.object(Collector, "_read_plist", autospec=True, return_value=plist) as mock_read_plist:
            self.collector._log_user_login_items()
            mock_read_plist.assert_called_with(self.collector, plist_path)
            self.mock_log_dict.assert_called_with(login_item)

    def test_collect_accounts_recent_items(self):
        plist_path = "/Users/test/Library/Preferences/com.apple.recentitems.plist"
        plist = {
            "RecentServers": {
                "CustomListItems": [
                    {"Name": "presidio"},
                    {"Name": "marina"},
                    {"Name": "sunset"},
                ],
            },
            "RecentDocuments": {
                "CustomListItems": [
                    {"Name": "russian_hill.jpg"},
                    {"Name": "nob_hill.jpg"},
                    {"Name": "rincon_hill.jpg"},
                ],
            },
            "RecentApplications": {
                "CustomListItems": [
                    {"Name": "Golden Gate Park"},
                    {"Name": "Glen Park"},
                    {"Name": "Jordan Park"},
                ],
            },
            "Hosts": {
                "CustomListItems": [
                    {"Name": "South of Market", "URL": "afp://sfo/soma"},
                    {"Name": "Financial District", "URL": "afp://sfo/fidi"},
                    {"Name": "North Beach", "URL": "afp://sfo/nobe"},
                ],
            },
        }
        recents = [
            {"server_name": "presidio"},
            {"server_name": "marina"},
            {"server_name": "sunset"},
            {"document_name": "russian_hill.jpg"},
            {"document_name": "nob_hill.jpg"},
            {"document_name": "rincon_hill.jpg"},
            {"application_name": "Golden Gate Park"},
            {"application_name": "Glen Park"},
            {"application_name": "Jordan Park"},
            {"host_name": "South of Market", "host_url": "afp://sfo/soma"},
            {"host_name": "Financial District", "host_url": "afp://sfo/fidi"},
            {"host_name": "North Beach", "host_url": "afp://sfo/nobe"},
        ]
        with patch.object(Collector, "_read_plist", autospec=True, return_value=plist) as mock_read_plist:
            self.collector._collect_accounts_recent_items()

            mock_read_plist.assert_called_with(self.collector, plist_path)
            for recent in recents:
                self.mock_log_dict.assert_any_call(recent)

    def assert_log(self, plist_path, expected_log):
        plist = self.collector._read_plist(plist_path)
        assert plist == {}
        self.mock_log_dict.assert_called_once_with(expected_log)

    def test_read_plist_file_not_found(self):
        plist_path = "tests/data/plists/non_existing.plist"
        warning = f"plist file not found. plist_path[{plist_path}]"
        expected_log = {
            "osxcollector_warn": warning,
        }
        self.assert_log(plist_path, expected_log)

    def test_read_plist_empty(self):
        plist_path = "tests/data/plists/empty.plist"
        warning = f"Empty plist. plist_path[{plist_path}]"
        expected_log = {
            "osxcollector_warn": warning,
        }
        self.assert_log(plist_path, expected_log)

    def test_read_plist_invalid_format(self):
        plist_path = "tests/data/plists/invalid_format.plist"
        plist = self.collector._read_plist(plist_path)
        assert plist == {}
        # Error message text may vary by Python/plistlib version
        assert self.mock_log_dict.call_count == 1
        logged = self.mock_log_dict.call_args[0][0]
        assert "osxcollector_error" in logged
        assert plist_path in logged["osxcollector_error"]

    def _mock_sqlite_connection(self):
        self.connect_mock = MagicMock()
        sqlite_utils.connect = self.connect_mock
        osxcollector.osxcollector.connect = self.connect_mock
        context_manager_mock = self.connect_mock.return_value
        self.conn_mock = context_manager_mock.__enter__.return_value

        self.cursor_mock = self.conn_mock.cursor.return_value
        tables = [
            ("boom", "duh", "fruits"),
            ("duff", "poom", "veggies"),
        ]
        rows_fruits = [
            ("apple", "green"),
            ("banana", "yellow"),
            ("cherry", "red"),
        ]
        rows_veggies = [
            ("carrot", "orange"),
            ("radish", "red"),
        ]
        self.cursor_mock.fetchall.side_effect = [
            tables,
            rows_fruits,
            rows_veggies,
        ]
        self.cursor_mock.description = [["name"], ["color"]]

    def test_log_sqlite_db(self):
        self._mock_sqlite_connection()

        with patch("os.path.isfile", autospec=True, return_value=True):
            self.collector._log_sqlite_db(
                "/Users/test/sqlite/db/panama_papers",
            )

        self.connect_mock.assert_any_call(
            "/Users/test/sqlite/db/panama_papers",
        )
        self.conn_mock.cursor.assert_any_call()
        assert self.cursor_mock.execute.mock_calls == [
            call('SELECT * from sqlite_master WHERE type = "table"'),
            call('SELECT * from "fruits"'),
            call('SELECT * from "veggies"'),
        ]

        assert self.mock_log_dict.mock_calls == [
            call({"name": "apple", "color": "green"}),
            call({"name": "banana", "color": "yellow"}),
            call({"name": "cherry", "color": "red"}),
            call({"name": "carrot", "color": "orange"}),
            call({"name": "radish", "color": "red"}),
        ]

    def test_log_sqlite_db_ignore(self):
        self._mock_sqlite_connection()

        with patch("os.path.isfile", autospec=True, return_value=True):
            self.collector._log_sqlite_db(
                "/Users/test/sqlite/db/cayman_airways",
                ignore={"fruits": ["color"]},
            )

        assert self.mock_log_dict.mock_calls == [
            call({"name": "apple"}),
            call({"name": "banana"}),
            call({"name": "cherry"}),
            call({"name": "carrot", "color": "orange"}),
            call({"name": "radish", "color": "red"}),
        ]
