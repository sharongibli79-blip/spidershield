"""Behavior tests. They do not use the network."""

import unittest

from spidershield import SafeAgentCrew, SafetyGuard, safe_execute


class GuardTests(unittest.TestCase):
    def test_read_allowed_delete_blocked(self):
        guard = SafetyGuard()
        self.assertTrue(guard.check_permission("file_read"))
        self.assertFalse(guard.check_permission("file_delete"))

    def test_restricted_write_needs_a_listed_resource(self):
        guard = SafetyGuard()
        self.assertFalse(guard.check_permission("file_write"))
        self.assertFalse(guard.check_permission("file_write", "notes/out.txt"))
        guard.allow_resource("file_write", "notes/out.txt")
        self.assertTrue(guard.check_permission("file_write", "notes/out.txt"))
        self.assertFalse(guard.check_permission("file_write", "other.txt"))

    def test_unknown_action_is_denied(self):
        guard = SafetyGuard()
        self.assertFalse(guard.check_permission("shell"))

    def test_open_for_write_is_flagged(self):
        guard = SafetyGuard()
        safe, warnings = guard.validate_code('open(path, "w")')
        self.assertFalse(safe)
        self.assertTrue(warnings)

    def test_delete_sentence_is_refused(self):
        guard = SafetyGuard()
        allowed, warnings = guard.assess_task("delete all files in /etc")
        self.assertFalse(allowed)
        self.assertTrue(any("file_delete" in item for item in warnings))

    def test_already_is_not_a_read(self):
        guard = SafetyGuard()
        allowed, warnings = guard.assess_task("the report is already done")
        self.assertTrue(allowed)
        self.assertEqual(warnings, [])

    def test_timeout_returns_without_waiting_the_full_sleep(self):
        @safe_execute(timeout_seconds=1)
        def slow(task, context):
            import time

            time.sleep(30)
            return task

        outcome = slow("x", None)
        self.assertFalse(outcome["success"])
        self.assertLess(outcome["elapsed_seconds"], 5)

    def test_rag_does_not_invent_a_download(self):
        crew = SafeAgentCrew()
        agent = crew.add_agent("Researcher", "Gather data")
        result = agent.execute_rag_query("Find climate data", ["wikipedia", "government"])
        blob = str(result)
        self.assertNotIn("Retrieved data", blob)
        by_source = {row["source"]: row for row in result["results"]}
        self.assertIsNone(by_source["wikipedia"]["data"])
        self.assertIsNone(by_source["government"]["data"])
        self.assertIn("no retriever", by_source["wikipedia"]["note"])
        self.assertIn("restricted", by_source["government"]["note"])

    def test_retriever_runs_only_after_allow(self):
        crew = SafeAgentCrew()
        agent = crew.add_agent("Researcher", "Gather data")
        seen = []

        def retriever(query, source):
            seen.append(source)
            return f"{query}:{source}"

        result = agent.execute_rag_query(
            "Find climate data",
            ["public_domain", "government"],
            retriever=retriever,
        )
        self.assertEqual(seen, ["public_domain"])
        by_source = {row["source"]: row for row in result["results"]}
        self.assertEqual(by_source["public_domain"]["data"], "Find climate data:public_domain")
        self.assertIsNone(by_source["government"]["data"])


if __name__ == "__main__":
    unittest.main()
