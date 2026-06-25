/**
 * Case Management Types
 * Defines the structure of case-related data across the application
 */

export type CaseStatus = 
  | 'Under Investigation'
  | 'Pending Trial'
  | 'Closed'
  | 'Convicted'
  | 'Charge Sheet Filed'
  | 'Arrested'
  | 'Bail Granted'
  | 'Acquitted'
  | 'Archived';

export interface Accused {
  id?: string;
  name: string;
  fatherName?: string;
  age?: string;
  gender?: string;
  address?: string;
  mobile?: string;
  status: string;
  photo?: string;
}

export interface Evidence {
  id?: string;
  name: string;
  type: 'document' | 'audio' | 'image' | 'video' | 'other';
  url?: string;
  uploadedAt?: string;
  metadata?: {
    content_type?: string;
    uploader?: string;
    uploader_role?: string;
    tx_hash?: string;
    [key: string]: any;
  };
}

export interface Case {
  id: string;
  caseNumber: string;
  district: string;
  unit: string;
  status: CaseStatus;
  lawSections: string[];
  dateOfOffence: string;
  dateOfReport: string;
  sceneOfCrime: string;
  latitude: number;
  longitude: number;
  description?: string;
  accused: Accused[];
  evidence: Evidence[];
  createdAt: string;
  updatedAt: string;
  hash?: string;
  tx_hash?: string;
  customFields?: Array<{
    name: string;
    value: any;
  }>;
  publicAlertEnabled?: boolean;
}

export interface CaseCreateRequest {
  district: string;
  unit: string;
  lawSections: string[];
  dateOfOffence: string;
  dateOfReport: string;
  sceneOfCrime: string;
  latitude: number;
  longitude: number;
  contrabandType?: string;
  contrabandQuantity?: string;
  vehicleDetails?: string;
  accused: Accused[];
  customFields?: Array<any>;
  publicAlertEnabled?: boolean;
  publicAlertMessage?: string;
  publicAlertMobile?: string;
}

export interface CasesListResponse {
  cases: Case[];
  error?: string;
}

export interface CaseDetailResponse {
  case: Case;
  error?: string;
}

export interface ApiError {
  message: string;
  statusCode?: number;
  timestamp?: string;
}
