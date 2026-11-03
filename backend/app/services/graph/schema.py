from enum import Enum


class NodeLabel(str, Enum):
    # Core Ingested Graph Labels
    WORKSPACE = "Workspace"
    PERSON = "Person"
    TEAM = "Team"
    DEPARTMENT = "Department"
    PROJECT = "Project"
    DOCUMENT = "Document"
    NOTEBOOK = "Notebook"
    FILE = "File"
    DECISION = "Decision"
    TASK = "Task"
    TICKET = "Ticket"
    EPISODEMEMORY = "EpisodeMemory"
    SOURCESYSTEM = "SourceSystem"
    PERMISSION = "Permission"


class RelationType(str, Enum):
    # Core Ingested Relationships
    CONTAINS = "CONTAINS"
    OWNS = "OWNS"
    MEMBER_OF = "MEMBER_OF"
    BELONGS_TO = "BELONGS_TO"
    DERIVED_FROM = "DERIVED_FROM"
    AUTHORED_BY = "AUTHORED_BY"
    CREATED_BY = "CREATED_BY"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"
    LINKED_TO_PROJECT = "LINKED_TO_PROJECT"
    MADE_BY = "MADE_BY"
