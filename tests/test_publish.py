import json
import unittest

from scripts.publish import pending_packages, publish_order, release_request, require_indexed, workspace_packages


def package(name, dependencies=(), version="0.2.1"):
    return {
        "id": name,
        "name": name,
        "version": version,
        "dependencies": [{"name": name} for name in dependencies],
        "publish": None,
    }


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.packages = {
            "oldwin": package("oldwin"),
            "oldwin-targets": package("oldwin-targets", ["oldwin-vc-ltl5"]),
            "oldwin-vc-ltl5": package("oldwin-vc-ltl5", ["oldwin-native"]),
            "oldwin-native": package("oldwin-native", version="0.2.1+5.3.1"),
        }

    def test_tag_push_uses_tag_version_and_enables_upload(self):
        self.assertEqual(
            release_request("push", "refs/tags/v0.2.1", "9.9.9", True),
            ("refs/tags/v0.2.1", "0.2.1", True),
        )

    def test_manual_dry_run_uses_current_main_commit(self):
        self.assertEqual(
            release_request("workflow_dispatch", "refs/heads/main", "v0.2.1", True),
            ("HEAD", "0.2.1", False),
        )

    def test_manual_upload_uses_release_tag_not_moving_main(self):
        self.assertEqual(
            release_request("workflow_dispatch", "refs/heads/main", "0.2.1", False),
            ("refs/tags/v0.2.1", "0.2.1", True),
        )

    def test_branch_push_and_non_main_manual_requests_are_rejected(self):
        for event, ref in [
            ("push", "refs/heads/main"),
            ("push", "refs/tags/release-0.2.1"),
            ("workflow_dispatch", "refs/heads/feature"),
            ("pull_request", "refs/pull/1/merge"),
        ]:
            with self.subTest(event=event, ref=ref):
                with self.assertRaises(ValueError):
                    release_request(event, ref, "0.2.1", False)

    def test_invalid_release_versions_are_rejected(self):
        for version in ["", "0.2", "01.2.1", "0.2.1\nupload=true", "0.2.1/branch"]:
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    release_request("workflow_dispatch", "refs/heads/main", version, False)

    def test_dependency_order_keeps_helper_last(self):
        order = publish_order(self.packages)
        self.assertLess(order.index("oldwin-native"), order.index("oldwin-vc-ltl5"))
        self.assertLess(order.index("oldwin-vc-ltl5"), order.index("oldwin-targets"))
        self.assertEqual(order[-1], "oldwin")

    def test_partial_release_skips_uploaded_native_version(self):
        uploaded = dict.fromkeys(self.packages)
        uploaded["oldwin-native"] = {"num": "0.2.1+5.3.1", "yanked": False}
        self.assertEqual(
            pending_packages(self.packages, uploaded),
            ["oldwin-vc-ltl5", "oldwin-targets", "oldwin"],
        )

    def test_yanked_release_is_not_silently_reused(self):
        uploaded = dict.fromkeys(self.packages)
        uploaded["oldwin-native"] = {"num": "0.2.1+5.3.1", "yanked": True}
        with self.assertRaisesRegex(ValueError, "yanked"):
            pending_packages(self.packages, uploaded)

    def test_wrong_existing_version_cannot_satisfy_release(self):
        uploaded = dict.fromkeys(self.packages)
        uploaded["oldwin-native"] = {"num": "0.2.0+5.3.1", "yanked": False}
        with self.assertRaisesRegex(ValueError, "mismatched"):
            pending_packages(self.packages, uploaded)

    def test_native_metadata_is_allowed_but_release_mismatch_is_rejected(self):
        metadata = {
            "workspace_members": list(self.packages),
            "packages": list(self.packages.values()),
        }
        self.assertEqual(workspace_packages(metadata, "v0.2.1"), self.packages)
        self.packages["oldwin-native"]["version"] = "0.2.0+5.3.1"
        with self.assertRaisesRegex(ValueError, "oldwin-native=0.2.0"):
            workspace_packages(metadata, "0.2.1")

    def test_unindexed_and_yanked_dependencies_block_publishing(self):
        old = json.dumps({"vers": "0.2.0+5.3.1", "yanked": False})
        yanked = json.dumps({"vers": "0.2.1+5.3.1", "yanked": True})
        for index in ("", old, old + "\n" + yanked):
            with self.subTest(index=index):
                with self.assertRaisesRegex(ValueError, "has not indexed"):
                    require_indexed("oldwin-native", "0.2.1+5.3.1", index)
        available = json.dumps({"vers": "0.2.1+5.3.1", "yanked": False})
        require_indexed("oldwin-native", "0.2.1+5.3.1", old + "\n" + available)


if __name__ == "__main__":
    unittest.main()
