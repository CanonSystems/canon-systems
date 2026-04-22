"""Core enums and canonical values used across the product layer."""

from __future__ import annotations

from enum import Enum


class CanonicalStrEnum(str, Enum):
    """String enum with stable lowercase values."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)


class ArtifactType(CanonicalStrEnum):
    CONVERSATION_TRANSCRIPT = "conversation_transcript"
    MEMORY_CAPTURE = "memory_capture"
    CURRENT_STATE_NOTE = "current_state_note"
    DECISION_RECORD = "decision_record"
    ARCHITECTURE_NOTE = "architecture_note"
    REPO_NOTE = "repo_note"
    PROJECT_NOTE = "project_note"
    TASK_CONTEXT = "task_context"
    PLAN_PACKET = "plan_packet"
    SCAFFOLD_BLUEPRINT = "scaffold_blueprint"
    SCOPE_PACKET = "scope_packet"
    EXECUTION_PACKET = "execution_packet"
    QA_PACKET = "qa_packet"
    JIRA_COMMENT_SNAPSHOT = "jira_comment_snapshot"
    SYNC_EVENT = "sync_event"


class Visibility(CanonicalStrEnum):
    PRIVATE = "private"
    TEAM = "team"
    PROJECT = "project"
    RESTRICTED = "restricted"


class ArtifactStatus(CanonicalStrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class RunStage(CanonicalStrEnum):
    INTAKE = "intake"
    CONTEXT_HYDRATION = "context_hydration"
    PATH_SELECTION = "path_selection"
    PROJECT_STRUCTURING = "project_structuring"
    STORY_SCOPING = "story_scoping"
    EXECUTION_PACKET = "execution_packet"
    IMPLEMENTATION = "implementation"
    PARALLEL_QA = "parallel_qa"
    PUBLISH_SYNC = "publish_sync"
    RECONCILIATION = "reconciliation"
    HUMAN_BLOCKED = "human_blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class RunLaunchMode(CanonicalStrEnum):
    INITIATIVE_LAUNCH = "initiative_launch"
    DELIVERY_LAUNCH = "delivery_launch"


class LinkType(CanonicalStrEnum):
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"
    SUPERSEDES = "supersedes"
    RELATED_TO = "related_to"
    ANSWERS = "answers"
    BLOCKS = "blocks"
    IMPLEMENTS = "implements"
    DOCUMENTS = "documents"
    ORIGINATED_FROM = "originated_from"


class ExternalRefType(CanonicalStrEnum):
    JIRA_ISSUE = "jira_issue"
    JIRA_COMMENT = "jira_comment"
    GIT_COMMIT = "git_commit"
    GIT_BRANCH = "git_branch"
    SLACK_THREAD = "slack_thread"
    SLACK_MESSAGE = "slack_message"
    OBSIDIAN_NOTE = "obsidian_note"
    MEMPALACE_DRAWER = "mempalace_drawer"


ALL_ARTIFACT_TYPE_VALUES = ArtifactType.values()
ALL_VISIBILITY_VALUES = Visibility.values()
ALL_ARTIFACT_STATUS_VALUES = ArtifactStatus.values()
ALL_RUN_STAGE_VALUES = RunStage.values()
ALL_RUN_LAUNCH_MODE_VALUES = RunLaunchMode.values()
ALL_LINK_TYPE_VALUES = LinkType.values()
ALL_EXTERNAL_REF_TYPE_VALUES = ExternalRefType.values()
