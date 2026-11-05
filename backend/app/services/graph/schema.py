from enum import Enum


class NodeLabel(str, Enum):
    # Tier 0: Context
    ORGANIZATION = "Organization"
    DOMAIN = "Domain"
    TEMPORAL_WINDOW = "TemporalWindow"

    # Tier 1: Structural
    PERSON = "Person"
    GROUP = "Group"
    LOCATION = "Location"
    ROLE = "Role"

    # Tier 2: Operational
    PROJECT = "Project"
    MILESTONE = "Milestone"
    TASK = "Task"
    SYSTEM = "System"
    PROCESS = "Process"

    # Tier 3: Events
    INCIDENT = "Incident"
    DECISION = "Decision"
    CHANGE = "Change"

    # Tier 4: Knowledge
    DOCUMENT = "Document"
    FINDING = "Finding"
    LESSON = "Lesson"
    ACTION = "Task"  # Action is synonymous with Task

    # Tier 5: Semantic
    CONCEPT = "Concept"
    METRIC = "Metric"

    # Databricks & Connector Overlays
    WORKSPACE = "Workspace"
    TEAM = "Group"
    NOTEBOOK = "Document"
    FILE = "Document"

    # Special Graph Overlays
    STUB = "Stub"
    EPISODEMEMORY = "EpisodeMemory"
    MULTI_CAUSE = "MULTI_CAUSE"
    UNCLASSIFIED = "Unclassified"


class RelationType(str, Enum):
    # Structural
    MANAGES = "MANAGES"
    MEMBER_OF = "MEMBER_OF"
    PART_OF = "PART_OF"
    BELONGS_TO = "PART_OF"
    CONTAINS = "PART_OF"
    OWNS = "MANAGES"
    LOCATED_AT = "LOCATED_AT"
    HELD_ROLE = "HELD_ROLE"
    OPERATES = "OPERATES"

    # Operational
    LEADS = "LEADS"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    ASSIGNED_TO = "ASSIGNED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    AFFECTS = "AFFECTS"

    # Causal
    CAUSED_BY = "CAUSED_BY"
    CAUSED_RECURRENCE = "CAUSED_RECURRENCE"
    UNBLOCKED_BY = "UNBLOCKED_BY"
    PREVENTED_BY = "PREVENTED_BY"
    DERIVED_FROM = "DERIVED_FROM"
    OVERRIDES = "OVERRIDES"

    # Knowledge
    AUTHORED_BY = "AUTHORED_BY"
    DOCUMENTS = "DOCUMENTS"
    SUPERSEDED_BY = "SUPERSEDED_BY"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    GENERALIZES = "GENERALIZES"

    # Temporal
    PRECEDED_BY = "PRECEDED_BY"
    TRIGGERED = "TRIGGERED"
    OCCURRED_DURING = "OCCURRED_DURING"
    RESOLVED_BY = "RESOLVED_BY"

    # Semantic & System
    SIMILAR_TO = "SIMILAR_TO"
    RELATED_TO = "RELATED_TO"
    MENTIONED_IN = "MENTIONED_IN"
    TAGGED_WITH = "TAGGED_WITH"
    ALIAS = "ALIAS"
    PENDING_RESOLUTION = "PENDING_RESOLUTION"
    TOUCHED = "TOUCHED"
