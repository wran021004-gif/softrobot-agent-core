"""Independent Knowledge/Skill role-gating tests.

These tests use synthetic resource metadata only. They do not create a Study,
call a Provider, access a Store, or execute scientific tools.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.research.contracts import KnowledgePolicy, ExperienceQuery
from tools.research import experience


def row(entry_id, role, *, kind="procedure", disclosure="answer_isolated",
        benchmark_sensitive=False):
    return dict(
        entry_id=entry_id,
        revision="1",
        kind=kind,
        resource_role=role,
        introduced_in="typed_knowledge_v1",
        disclosure=disclosure,
        benchmark_sensitive=benchmark_sensitive,
        status="public_procedural_guidance; generalization_unverified",
        task="soft_robot_research",
        path="memory/not-read-by-this-test.json",
    )


def spec_for(roles, entries):
    policy = KnowledgePolicy(
        organization="typed_knowledge_v1",
        allowed_resource_roles=roles,
    )
    return dict(
        study_id="role-gate-fixture",
        knowledge=policy.model_dump(mode="json"),
        knowledge_manifest=dict(entries=entries),
        study_experience_entries=[],
    )


class KnowledgeSkillRoleGating(unittest.TestCase):
    def test_policy_preserves_legacy_when_roles_are_unspecified(self):
        policy = KnowledgePolicy(organization="typed_knowledge_v1")
        self.assertIsNone(policy.allowed_resource_roles)
        self.assertNotIn("allowed_resource_roles", policy.model_dump(mode="json"))

    def test_duplicate_roles_are_rejected(self):
        with self.assertRaises(ValueError):
            KnowledgePolicy(allowed_resource_roles=["knowledge", "knowledge"])

    def test_knowledge_only_and_skill_only_are_independent(self):
        rows = [row("k1", "knowledge"), row("s1", "skill")]
        host = SimpleNamespace()
        for roles, expected in [
            (["knowledge"], ["k1"]),
            (["skill"], ["s1"]),
            ([], []),
        ]:
            spec = spec_for(roles, rows)
            with self.subTest(roles=roles), patch.object(
                experience, "state", return_value={"spec": spec}
            ):
                actual = experience.entries(host)
            self.assertEqual([r["entry_id"] for r in actual], expected)

    def test_role_filter_applies_to_all_retrieval_authorization(self):
        knowledge = row("k1", "knowledge")
        skill = row("s1", "skill")
        knowledge_policy = KnowledgePolicy(
            organization="typed_knowledge_v1",
            allowed_resource_roles=["knowledge"],
        ).model_dump(mode="json")
        skill_policy = KnowledgePolicy(
            organization="typed_knowledge_v1",
            allowed_resource_roles=["skill"],
        ).model_dump(mode="json")
        self.assertTrue(experience._permitted(knowledge, knowledge_policy))
        self.assertFalse(experience._permitted(skill, knowledge_policy))
        self.assertTrue(experience._permitted(skill, skill_policy))
        self.assertFalse(experience._permitted(knowledge, skill_policy))

    def test_empty_role_list_keeps_interface_but_authorizes_no_resource(self):
        policy = KnowledgePolicy(
            organization="typed_knowledge_v1",
            allowed_resource_roles=[],
        ).model_dump(mode="json")
        self.assertFalse(experience._permitted(row("k1", "knowledge"), policy))
        self.assertFalse(experience._permitted(row("s1", "skill"), policy))

    def test_benchmark_sensitive_and_draft_resources_remain_blocked(self):
        policy = KnowledgePolicy(
            organization="typed_knowledge_v1",
            allowed_resource_roles=["knowledge"],
            allow_benchmark_answers=False,
        ).model_dump(mode="json")
        sensitive = row(
            "case1", "knowledge", kind="success_case",
            disclosure="restricted_full_trace", benchmark_sensitive=True,
        )
        draft = row(
            "draft1", "knowledge", kind="case",
            disclosure="draft_only", benchmark_sensitive=False,
        )
        self.assertFalse(experience._permitted(sensitive, policy))
        self.assertFalse(experience._permitted(draft, policy))

    def test_exact_query_can_select_each_resource_role(self):
        for role in ("knowledge", "skill"):
            query = ExperienceQuery(operation="search", knowledge_type=role)
            self.assertEqual(query.knowledge_type, role)


if __name__ == "__main__":
    unittest.main()
