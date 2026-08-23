from creator_app.agnes.adaptive_runtime.approval_inheritance import ApprovalMode, effective_child_mode
from creator_app.agnes.adaptive_runtime.context_fork import ContextForkPlan
from creator_app.agnes.adaptive_runtime.namespace_resolver import resolve_name
from creator_app.agnes.adaptive_runtime.skill_activation import SkillActivationPolicy
from creator_app.agnes.adaptive_runtime.worktree_policy import WorktreeExecutionPolicy


def test_skill_path_gate_and_no_authority():
    policy = SkillActivationPolicy(name="python-review", path_patterns=("*.py",))
    assert policy.is_active(touched_paths=("app.py",))
    assert not policy.is_active(touched_paths=("README.md",))
    assert policy.grants_execution_authority() is False


def test_context_fork_bounded_mode():
    plan = ContextForkPlan(recent_user_turns=3)
    assert plan.mode() == "LAST_3_USER_TURNS"
    assert plan.share_prompt_cache_prefix is True
    assert plan.include_tool_outputs is False


def test_child_cannot_escalate_parent():
    assert effective_child_mode(ApprovalMode.PLAN, ApprovalMode.AUTONOMOUS) == ApprovalMode.PLAN
    assert effective_child_mode(ApprovalMode.DEFAULT, ApprovalMode.AUTO_EDIT) == ApprovalMode.DEFAULT


def test_extension_name_collision_is_namespaced():
    assert resolve_name(requested="deploy", extension="qwen", occupied={"deploy"}) == "qwen.deploy"


def test_caller_owned_worktree_forces_foreground():
    policy = WorktreeExecutionPolicy(
        ck_managed_isolation=True,
        caller_owned_worktree=True,
        requested_background=True,
    )
    assert policy.execution_mode() == "FOREGROUND"
    assert policy.can_fork_context() is False
