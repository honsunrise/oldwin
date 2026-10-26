import json
import unittest

from scripts.publish import pending_packages, publish_order, require_indexed, workspace_packages


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
