export interface Accused {
  id: string;
  name: string;
  fatherName: string;
  age: number;
  gender: 'Male' | 'Female' | 'Other';
  address: string;
  mobile?: string;
  status: 'Arrested' | 'Absconding' | 'Released on Bail' | 'Under Investigation';
  photo?: string;
}

export interface Evidence {
  id: string;
  type: 'image' | 'document' | 'video' | 'audio';
  name: string;
  url: string;
  uploadedAt: string;
  metadata?: Record<string, string>;
}

export interface Case {
  id: string;
  caseNumber: string;
  district: string;
  unit: string;
  lawSections: string[];
  dateOfOffence: string;
  dateOfReport: string;
  sceneOfCrime: string;
  latitude: number;
  longitude: number;
  status: 'Under Investigation' | 'Pending Trial' | 'Closed' | 'Convicted';
  contrabandType?: string;
  contrabandQuantity?: string;
  vehicleDetails?: string;
  accused: Accused[];
  evidence: Evidence[];
  aiSummary?: string;
  createdAt: string;
  updatedAt: string;
  customFields?: Record<string, string>;
}

export const mockCases: Case[] = [
  {
    id: '1',
    caseNumber: 'CR-2024-001',
    district: 'Central Delhi',
    unit: 'Cyber Crime Unit',
    lawSections: ['IPC 420', 'IT Act 66C', 'IT Act 66D'],
    dateOfOffence: '2024-01-15',
    dateOfReport: '2024-01-16',
    sceneOfCrime: 'Connaught Place, New Delhi',
    latitude: 28.6315,
    longitude: 77.2167,
    status: 'Under Investigation',
    contrabandType: 'Digital Evidence',
    accused: [
      {
        id: 'a1',
        name: 'Rajesh Kumar',
        fatherName: 'Suresh Kumar',
        age: 32,
        gender: 'Male',
        address: '45, Lajpat Nagar, New Delhi',
        mobile: '9876543210',
        status: 'Arrested',
      },
    ],
    evidence: [
      {
        id: 'e1',
        type: 'document',
        name: 'Bank Statement.pdf',
        url: '/evidence/doc1.pdf',
        uploadedAt: '2024-01-16',
        metadata: { pages: '12', size: '2.4MB' },
      },
      {
        id: 'e2',
        type: 'image',
        name: 'Screenshot_evidence.png',
        url: '/evidence/img1.png',
        uploadedAt: '2024-01-16',
      },
    ],
    aiSummary: 'This case involves alleged cyber fraud where the accused reportedly created fake e-commerce websites to defraud customers. Digital evidence suggests transactions worth approximately ₹15 lakhs were routed through multiple bank accounts. Key evidence includes bank statements, IP logs, and victim testimonies.',
    createdAt: '2024-01-16',
    updatedAt: '2024-01-20',
  },
  {
    id: '2',
    caseNumber: 'CR-2024-002',
    district: 'South Delhi',
    unit: 'Narcotics Control Bureau',
    lawSections: ['NDPS Act 21', 'NDPS Act 22'],
    dateOfOffence: '2024-01-20',
    dateOfReport: '2024-01-20',
    sceneOfCrime: 'Nehru Place, New Delhi',
    latitude: 28.5494,
    longitude: 77.2519,
    status: 'Pending Trial',
    contrabandType: 'Narcotic Substances',
    contrabandQuantity: '500 grams',
    vehicleDetails: 'DL 4C AB 1234 - White Honda City',
    accused: [
      {
        id: 'a2',
        name: 'Amit Singh',
        fatherName: 'Ramesh Singh',
        age: 28,
        gender: 'Male',
        address: '78, Saket, New Delhi',
        status: 'Arrested',
      },
      {
        id: 'a3',
        name: 'Priya Sharma',
        fatherName: 'Vikram Sharma',
        age: 25,
        gender: 'Female',
        address: '23, Malviya Nagar, New Delhi',
        status: 'Released on Bail',
      },
    ],
    evidence: [
      {
        id: 'e3',
        type: 'image',
        name: 'Seized_contraband.jpg',
        url: '/evidence/img2.jpg',
        uploadedAt: '2024-01-20',
      },
      {
        id: 'e4',
        type: 'video',
        name: 'CCTV_footage.mp4',
        url: '/evidence/vid1.mp4',
        uploadedAt: '2024-01-20',
        metadata: { duration: '15:32', resolution: '1080p' },
      },
    ],
    aiSummary: 'Narcotics seizure case involving two suspects apprehended during a routine vehicle check. Approximately 500 grams of controlled substance was recovered from a hidden compartment. CCTV footage from nearby establishments corroborates the timeline of events.',
    createdAt: '2024-01-20',
    updatedAt: '2024-01-25',
  },
  {
    id: '3',
    caseNumber: 'CR-2024-003',
    district: 'North Delhi',
    unit: 'Economic Offences Wing',
    lawSections: ['IPC 406', 'IPC 409', 'Companies Act 447'],
    dateOfOffence: '2024-02-01',
    dateOfReport: '2024-02-05',
    sceneOfCrime: 'Chandni Chowk, Delhi',
    latitude: 28.6506,
    longitude: 77.2303,
    status: 'Under Investigation',
    accused: [
      {
        id: 'a4',
        name: 'Vikram Malhotra',
        fatherName: 'Ashok Malhotra',
        age: 45,
        gender: 'Male',
        address: '156, Civil Lines, Delhi',
        mobile: '9988776655',
        status: 'Absconding',
      },
    ],
    evidence: [
      {
        id: 'e5',
        type: 'document',
        name: 'Company_records.pdf',
        url: '/evidence/doc2.pdf',
        uploadedAt: '2024-02-05',
      },
    ],
    aiSummary: 'Financial fraud case involving misappropriation of company funds. The accused, a former director, allegedly siphoned approximately ₹2.5 crore through fraudulent invoices and shell companies. Investigation ongoing to trace the flow of funds.',
    createdAt: '2024-02-05',
    updatedAt: '2024-02-10',
  },
  {
    id: '4',
    caseNumber: 'CR-2024-004',
    district: 'West Delhi',
    unit: 'Crime Branch',
    lawSections: ['IPC 302', 'IPC 201'],
    dateOfOffence: '2024-02-10',
    dateOfReport: '2024-02-10',
    sceneOfCrime: 'Rajouri Garden, New Delhi',
    latitude: 28.6469,
    longitude: 77.1187,
    status: 'Closed',
    accused: [
      {
        id: 'a5',
        name: 'Sanjay Verma',
        fatherName: 'Mahesh Verma',
        age: 38,
        gender: 'Male',
        address: '89, Tilak Nagar, New Delhi',
        status: 'Arrested',
      },
    ],
    evidence: [
      {
        id: 'e6',
        type: 'image',
        name: 'Crime_scene_1.jpg',
        url: '/evidence/img3.jpg',
        uploadedAt: '2024-02-10',
        metadata: { location: 'Primary scene', photographer: 'FSL Team' },
      },
      {
        id: 'e7',
        type: 'document',
        name: 'Forensic_report.pdf',
        url: '/evidence/doc3.pdf',
        uploadedAt: '2024-02-15',
        metadata: { lab: 'Central Forensic Science Laboratory' },
      },
    ],
    aiSummary: 'Homicide case with the accused apprehended within 48 hours. Forensic evidence including DNA matching and fingerprint analysis conclusively linked the accused to the crime scene. Case has been filed with chargesheet submitted to the court.',
    createdAt: '2024-02-10',
    updatedAt: '2024-02-20',
  },
  {
    id: '5',
    caseNumber: 'CR-2024-005',
    district: 'East Delhi',
    unit: 'Anti-Corruption Branch',
    lawSections: ['Prevention of Corruption Act 7', 'IPC 13'],
    dateOfOffence: '2024-02-15',
    dateOfReport: '2024-02-16',
    sceneOfCrime: 'Preet Vihar, New Delhi',
    latitude: 28.6358,
    longitude: 77.2931,
    status: 'Convicted',
    accused: [
      {
        id: 'a6',
        name: 'Sunil Gupta',
        fatherName: 'Ramesh Gupta',
        age: 52,
        gender: 'Male',
        address: '34, Shahdara, Delhi',
        status: 'Arrested',
      },
    ],
    evidence: [
      {
        id: 'e8',
        type: 'video',
        name: 'Sting_operation.mp4',
        url: '/evidence/vid2.mp4',
        uploadedAt: '2024-02-16',
      },
      {
        id: 'e9',
        type: 'audio',
        name: 'Phone_recording.mp3',
        url: '/evidence/aud1.mp3',
        uploadedAt: '2024-02-16',
      },
    ],
    aiSummary: 'Corruption case involving a public servant caught accepting bribe during a sting operation. Video and audio evidence clearly establish the demand and acceptance of illegal gratification. Court has pronounced guilty verdict with sentencing pending.',
    createdAt: '2024-02-16',
    updatedAt: '2024-03-01',
  },
];

export const districts = [
  'Central Delhi',
  'North Delhi',
  'South Delhi',
  'East Delhi',
  'West Delhi',
  'North East Delhi',
  'North West Delhi',
  'South East Delhi',
  'South West Delhi',
  'Shahdara',
  'New Delhi',
];

export const caseStatuses = [
  'Under Investigation',
  'Pending Trial',
  'Closed',
  'Convicted',
  'Charge Sheet Filed',
  'Arrested',
  'Bail Granted',
  'Acquitted',
];

export const contrabandTypes = [
  'Narcotic Substances',
  'Arms & Ammunition',
  'Counterfeit Currency',
  'Stolen Property',
  'Digital Evidence',
  'Documents',
  'Other',
];

export const accusedStatuses = [
  'Arrested',
  'Absconding',
  'Released on Bail',
  'Under Investigation',
];