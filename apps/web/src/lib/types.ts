export type User = {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  role: string;
};

export type Category = { id: string; name: string; slug: string };

export type Label = { id: string; name: string; slug: string; kind: string };

export type Milestone = {
  id: string;
  title: string;
  description: string | null;
  type: string;
  starts_at: string | null;
  ends_at: string | null;
  visibility: string;
  reminder_enabled: boolean;
  version: number;
  position: number;
};

export type Resource = { id: string; title: string; url: string; kind: string; position: number };

export type HackathonCard = {
  id: string;
  slug: string;
  name: string;
  organiser: string;
  organiser_logo_url: string | null;
  short_description: string | null;
  categories: Category[];
  mode: string | null;
  participation_type: string | null;
  difficulty: string | null;
  registration_state: string;
  registration_closes_at: string | null;
  submission_deadline: string | null;
  min_team_size: number | null;
  max_team_size: number | null;
  prize_pool: string | null;
  next_deadline_at: string | null;
  next_deadline_title: string | null;
  featured: boolean;
  lifecycle: string;
  timezone: string;
  published_at: string | null;
  updated_at: string;
  labels?: Label[];
};

export type HackathonPublic = HackathonCard & {
  description: string | null;
  problem_statements: string | null;
  official_website: string | null;
  banner_url: string | null;
  eligibility: string | null;
  academic_year: string | null;
  degree_requirements: string | null;
  geographic_restrictions: string | null;
  other_eligibility: string | null;
  venue: string | null;
  location: string | null;
  event_duration: string | null;
  registration_url: string | null;
  registration_opens_at: string | null;
  registration_instructions: string | null;
  submission_url: string | null;
  required_deliverables: string | null;
  submission_instructions: string | null;
  first_prize: string | null;
  second_prize: string | null;
  third_prize: string | null;
  special_awards: string | null;
  certificates: string | null;
  internships: string | null;
  other_rewards: string | null;
  preparation_guidelines: string | null;
  labels: Label[];
  milestones: Milestone[];
  resources: Resource[];
  tracks: Track[];
  deliverables: Deliverable[];
  prizes: Prize[];
  judging_criteria: JudgingCriterion[];
  faqs: Faq[];
  announcements: Announcement[];
  section_states: SectionState[];
  queries: StudentQuery[];
  following: boolean;
  bookmarked: boolean;
  stance: "registered" | "missed" | null;
  interested: boolean;
};

export type Track = { id: string; name: string; requirements: string | null; position: number };
export type Deliverable = { id: string; title: string; detail: string | null; required: boolean; position: number };
export type Prize = { id: string; label: string; detail: string | null; position: number };
export type JudgingCriterion = { id: string; title: string; detail: string | null; weight: number | null; position: number };
export type Faq = { id: string; question: string; answer: string; position: number };
export type Announcement = { id: string; title: string; body: string; published_at: string | null; position: number };
export type SectionState = { section: string; state: string };
export type QueryResponse = { id: string; body: string; official: boolean; created_at: string };
export type StudentQuery = {
  id: string;
  body: string;
  is_public: boolean;
  status: string;
  created_at: string;
  responses: QueryResponse[];
};
export type AppNotification = {
  id: string;
  hackathon_id: string | null;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

export type MyQuery = {
  id: string;
  hackathon_name: string;
  hackathon_slug: string;
  body: string;
  is_public: boolean;
  status: string;
  created_at: string;
  responses: QueryResponse[];
};

export type AdminQuery = MyQuery & {
  hackathon_id: string;
  author_name: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
};

export type AdminAnnouncement = {
  id: string;
  hackathon_id: string;
  hackathon_name: string;
  title: string;
  published_at: string | null;
};

export type HackathonAdmin = HackathonPublic & {
  created_by: string | null;
  internal: {
    internal_notes: string | null;
    tracking_status: string | null;
    administrative_comments: string | null;
    verification_status: string;
    last_verified_at: string | null;
    source_urls: string | null;
  };
  coordinators: User[];
};

export type HomePayload = {
  featured: HackathonCard[];
  recent: HackathonCard[];
  categories: Category[];
  due: HackathonCard[];
  deadlines: CalendarEvent[];
  registration_closed: HackathonCard[];
};

export type PageResult<T> = { items: T[]; page: number; page_size: number; total: number };

export type CalendarEvent = {
  id: string;
  title: string;
  hackathon_name: string;
  hackathon_slug: string;
  type: string;
  starts_at: string | null;
  ends_at: string | null;
  timezone: string;
};

export type Activity = {
  id: string;
  action: string;
  entity_type: string;
  summary: string;
  created_at: string;
};

export type Stats = {
  total: number;
  published: number;
  draft: number;
  registration_open: number;
  upcoming_deadlines: number;
  completed: number;
  recent_activity: Activity[];
};
