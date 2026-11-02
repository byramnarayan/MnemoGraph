from typing import Any
from app.connectors.databricks.models import (
    InternalCluster,
    InternalFile,
    InternalJob,
    InternalNotebook,
    InternalProject,
    InternalTeam,
    InternalUser,
)


class DatabricksMapper:
    """Translates raw Databricks SCIM / Workspace JSON payloads into normalized internal entities."""

    @staticmethod
    def map_user(raw: dict[str, Any]) -> InternalUser:
        emails = raw.get("emails", [])
        primary_email = ""
        for em in emails:
            if isinstance(em, dict) and em.get("value"):
                primary_email = em["value"]
                break
        if not primary_email and raw.get("userName"):
            primary_email = raw["userName"]

        display_name = raw.get("displayName") or primary_email or f"User-{raw.get('id')}"
        dept = raw.get("department")

        return InternalUser(
            source_id=str(raw.get("id") or primary_email),
            email=primary_email.lower(),
            display_name=display_name,
            department=dept,
            active=raw.get("active", True),
        )

    @staticmethod
    def map_group(raw: dict[str, Any]) -> InternalTeam:
        name = raw.get("displayName") or f"Group-{raw.get('id')}"
        members = [str(m.get("value")) for m in raw.get("members", []) if isinstance(m, dict)]
        return InternalTeam(
            source_id=str(raw.get("id") or name),
            name=name,
            member_source_ids=members,
        )

    @staticmethod
    def map_workspace_item(raw: dict[str, Any], workspace_id: str) -> InternalNotebook | InternalFile | InternalProject | None:
        obj_type = raw.get("object_type")
        path = raw.get("path", "")
        parts = [p for p in path.split("/") if p]
        title = parts[-1] if parts else "untitled"
        object_id = str(raw.get("object_id") or path)

        # Detect project / initiative folder
        if obj_type == "DIRECTORY":
            if len(parts) >= 1 and parts[0] not in ("Users", "Shared", "Repos"):
                return InternalProject(
                    source_id=f"proj:{object_id}",
                    name=title,
                    workspace_id=workspace_id,
                )
            return None

        # Derive project_id from directory structure if nested
        derived_project_id = parts[0] if len(parts) > 1 and parts[0] not in ("Users", "Shared", "Repos") else None
        owner_email = parts[1].lower() if len(parts) > 1 and parts[0] == "Users" else None

        if obj_type == "NOTEBOOK":
            return InternalNotebook(
                source_id=f"notebook:{object_id}",
                title=title,
                path=path,
                language=raw.get("language", "PYTHON"),
                workspace_id=workspace_id,
                project_id=derived_project_id,
                owner_email=owner_email,
            )
        elif obj_type == "FILE":
            return InternalFile(
                source_id=f"file:{object_id}",
                title=title,
                path=path,
                file_type=raw.get("file_type", "GENERIC"),
                workspace_id=workspace_id,
                project_id=derived_project_id,
                owner_email=owner_email,
            )
        return None

    @staticmethod
    def map_job(raw: dict[str, Any]) -> InternalJob:
        settings = raw.get("settings", {})
        tasks = settings.get("tasks", [])
        notebook_paths = []
        for t in tasks:
            nb_task = t.get("notebook_task")
            if nb_task and nb_task.get("notebook_path"):
                notebook_paths.append(nb_task["notebook_path"])

        job_id = str(raw.get("job_id"))
        return InternalJob(
            source_id=f"job:{job_id}",
            name=settings.get("name") or f"Job {job_id}",
            creator_user_name=raw.get("creator_user_name"),
            cluster_id=settings.get("existing_cluster_id"),
            notebook_paths=notebook_paths,
        )

    @staticmethod
    def map_cluster(raw: dict[str, Any]) -> InternalCluster:
        cid = str(raw.get("cluster_id"))
        return InternalCluster(
            source_id=f"cluster:{cid}",
            cluster_name=raw.get("cluster_name") or f"Cluster {cid}",
            creator_user_name=raw.get("creator_user_name"),
            state=raw.get("state", "RUNNING"),
        )
