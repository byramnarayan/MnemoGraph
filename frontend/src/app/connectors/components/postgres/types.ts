export interface PostgresConnectionConfig {
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode: string;
}

export interface DiscoveredColumn {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  is_cursor_candidate: boolean;
}

export interface DiscoveredTable {
  schema_name: string;
  table_name: string;
  primary_keys: string[];
  suggested_cursor_col?: string | null;
  suggested_entity_type: string;
  columns: DiscoveredColumn[];
}

export interface TableMappingSelection {
  enabled: boolean;
  entity_type: string;
  cursor_column?: string | null;
}

export const ONTOLOGY_CLASSES = [
  'Person',
  'Project',
  'Decision',
  'Incident',
  'Lesson',
  'Task',
  'System',
  'Document',
] as const;

