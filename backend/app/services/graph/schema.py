from enum import Enum


class NodeLabel(str, Enum):
    PERSON = "Person"
    TEAM = "Team"
    DEPARTMENT = "Department"
    PROJECT = "Project"
    WORKSPACE = "Workspace"
    DOCUMENT = "Document"
    NOTEBOOK = "Notebook"
    FILE = "File"
    DECISION = "Decision"
    TASK = "Task"
    TICKET = "Ticket"
    SOURCESYSTEM = "SourceSystem"
    PERMISSION = "Permission"


class RelationType(str, Enum):
    MEMBER_OF = "MEMBER_OF"
    BELONGS_TO = "BELONGS_TO"
    OWNS = "OWNS"
    AUTHORED_BY = "AUTHORED_BY"
    CREATED_BY = "CREATED_BY"
    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    MENTIONS = "MENTIONS"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"
    HAS_PERMISSION = "HAS_PERMISSION"
    DERIVED_FROM = "DERIVED_FROM"
    WORKED_ON = "WORKED_ON"
