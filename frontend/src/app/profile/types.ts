export interface DiscoveredPerson {
  entity_id: string;
  full_name: string;
  inferred_department?: string | null;
  inferred_role?: string | null;
  source_documents: string[];
  mention_count: number;
  has_existing_user: boolean;
  is_provisioned: boolean;
}

export interface ProvisionUserPayload {
  person_entity_id: string;
  full_name: string;
  email: string;
  password: string;
  role: string;
  department?: string;
  clearance_level: string;
  title?: string;
  location?: string;
}

export interface ProvisionedUserResponse {
  user_id: number;
  email: string;
  full_name: string;
  person_entity_id: string;
  role: string;
  clearance_level: string;
  is_synced_to_graph: boolean;
  message: string;
}

