from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InternalUser:
    source_id: str
    email: str
    display_name: str
    role: str = "Member"
    department: str | None = None
    active: bool = True


@dataclass
class InternalTeam:
    source_id: str
    name: str
    department: str | None = None
    member_source_ids: list[str] = field(default_factory=list)


@dataclass
class InternalProject:
    source_id: str
    name: str
    workspace_id: str
    owner_team: str | None = None


@dataclass
class InternalNotebook:
    source_id: str
    title: str
    path: str
    language: str
    workspace_id: str
    project_id: str | None = None
    owner_email: str | None = None
    content: str = ""
    modified_at: datetime | None = None


@dataclass
class InternalFile:
    source_id: str
    title: str
    path: str
    file_type: str
    workspace_id: str
    project_id: str | None = None
    owner_email: str | None = None
    content: str = ""


@dataclass
class InternalJob:
    source_id: str
    name: str
    creator_user_name: str | None = None
    cluster_id: str | None = None
    notebook_paths: list[str] = field(default_factory=list)


@dataclass
class InternalCluster:
    source_id: str
    cluster_name: str
    creator_user_name: str | None = None
    state: str = "RUNNING"
