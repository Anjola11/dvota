# Product Requirements Document (PRD)
## Voting System Platform

**Version:** 1.0  
**Last Updated:** November 17, 2025  
**Stack:** FastAPI + Supabase PostgreSQL + Cloudinary

---

## 1. Product Overview

### 1.1 Purpose
A backend system that enables users to create, manage, and conduct elections with multiple posts (positions) and candidates. Users can vote, view live results, and export data.

### 1.2 Target Users
- **Election Creators**: Users who create and manage elections
- **Voters**: Users who participate in elections by casting votes

### 1.3 Technology Stack
- **Backend Framework**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Image Storage**: Cloudinary
- **Authentication**: JWT (custom implementation)

---

## 2. Core Features & User Flows

### 2.1 User Authentication

#### Registration Flow
1. User submits: name, email, password
2. System validates email uniqueness
3. Password is hashed and stored
4. User account created
5. Return success response

#### Login Flow
1. User submits: email, password
2. System validates credentials
3. Generate JWT access token (15-30 min expiry)
4. Generate JWT refresh token (7-30 days expiry)
5. Return both tokens to user

#### Token Refresh Flow
1. User submits refresh token
2. System validates refresh token
3. Generate new access token
4. Return new access token

---

### 2.2 Election Creation Flow

#### Step 1: Create Election
**User Action**: POST `/elections`

**Required Data**:
- Title
- Description
- Start time (datetime)
- End time (datetime)
- Visibility (public/private)

**System Actions**:
1. Validate user is authenticated
2. Store election with `owner_id = current_user.id`
3. Generate unique `election_id`
4. Return election details + shareable link

**Response Includes**:
- `election_id`
- Shareable URL
- All submitted data

---

#### Step 2: Add Posts to Election
**User Action**: POST `/elections/{election_id}/posts`

**Required Data**:
- Title (e.g., "President", "General Secretary")

**System Actions**:
1. Validate user owns this election
2. Create post linked to election
3. Return post details

**Example Posts**:
- President
- General Secretary
- Welfare Director

---

#### Step 3: Add Candidates to Posts
**User Action**: POST `/posts/{post_id}/candidates`

**Required Data**:
- Name
- Bio
- Image file

**System Actions**:
1. Upload image to Cloudinary
2. Receive `image_url` from Cloudinary
3. Store candidate data with:
   - name
   - bio
   - image_url
   - post_id
4. Return candidate details

**Cloudinary Integration**:
- Accept image upload (JPEG, PNG)
- Auto-optimize image
- Return secure CDN URL
- Store URL in database

---

### 2.3 Voting Flow

#### Prerequisites Check
Before allowing vote, system must verify:
1. ✅ User is authenticated
2. ✅ Election is currently active (current time between start_time and end_time)
3. ✅ User has NOT already voted for this post
4. ✅ User is allowed to vote (if private election)

#### Vote Submission
**User Action**: POST `/votes`

**Required Data**:
- `election_id`
- `post_id`
- `candidate_id`

**System Actions**:
1. Run all prerequisite checks
2. If all pass, insert vote record:
   ```
   user_id: current_user.id
   election_id: from request
   post_id: from request
   candidate_id: from request
   timestamp: current datetime
   ```
3. Return success confirmation

**Database Constraint**:
- `UNIQUE (user_id, post_id)` ensures one vote per user per post

---

### 2.4 Results & Analytics

#### Live Results Endpoint
**User Action**: GET `/elections/{election_id}/results`

**System Response**:
For each post in the election, return:
- Post title
- List of candidates with:
  - Candidate name
  - Vote count
  - Percentage of total votes for that post

**Update Frequency**: Frontend can poll this endpoint every 5 seconds

**Example Response Structure**:
```json
{
  "election_id": "uuid",
  "title": "School Election 2025",
  "posts": [
    {
      "post_id": "uuid",
      "title": "President",
      "total_votes": 150,
      "candidates": [
        {
          "candidate_id": "uuid",
          "name": "John Doe",
          "votes": 90,
          "percentage": 60.0
        },
        {
          "candidate_id": "uuid",
          "name": "Jane Smith",
          "votes": 60,
          "percentage": 40.0
        }
      ]
    }
  ]
}
```

---

#### Owner Dashboard
**User Action**: GET `/elections/{election_id}/dashboard`

**Access Control**: Only election owner can access

**System Response**:
- Total number of unique voters
- Total votes cast (across all posts)
- Breakdown by post:
  - Post title
  - Number of votes
  - Candidates with vote counts
- Activity logs (optional)

---

### 2.5 Data Export

#### Export Formats
Election owner can download results in:
- PDF
- CSV
- Excel

**Endpoints**:
- GET `/elections/{election_id}/download/pdf`
- GET `/elections/{election_id}/download/csv`
- GET `/elections/{election_id}/download/excel`

**Access Control**: Only election owner

**System Actions**:
1. Validate user owns election
2. Generate file on-the-fly
3. Return file for download

**Export Contents**:
- Election metadata (title, dates, etc.)
- Each post with candidate results
- Vote counts and percentages
- Total statistics

---

## 3. Database Schema

### 3.1 Tables

#### users
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
name              TEXT NOT NULL
email             TEXT UNIQUE NOT NULL
password_hash     TEXT NOT NULL
created_at        TIMESTAMP DEFAULT NOW()
```

#### elections
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
owner_id          UUID REFERENCES users(id) ON DELETE CASCADE
title             TEXT NOT NULL
description       TEXT
visibility        TEXT CHECK (visibility IN ('public', 'private'))
start_time        TIMESTAMP NOT NULL
end_time          TIMESTAMP NOT NULL
created_at        TIMESTAMP DEFAULT NOW()
```

#### posts
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
election_id       UUID REFERENCES elections(id) ON DELETE CASCADE
title             TEXT NOT NULL
```

#### candidates
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
post_id           UUID REFERENCES posts(id) ON DELETE CASCADE
name              TEXT NOT NULL
bio               TEXT
image_url         TEXT NOT NULL
```

#### votes
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
election_id       UUID REFERENCES elections(id) ON DELETE CASCADE
post_id           UUID REFERENCES posts(id) ON DELETE CASCADE
candidate_id      UUID REFERENCES candidates(id) ON DELETE CASCADE
user_id           UUID REFERENCES users(id) ON DELETE CASCADE
timestamp         TIMESTAMP DEFAULT NOW()

CONSTRAINT unique_vote_per_post UNIQUE (user_id, post_id)
```

### 3.2 Key Relationships
- One user can create **many elections** (1:M)
- One election has **many posts** (1:M)
- One post has **many candidates** (1:M)
- One user can cast **many votes** (1:M)
- One vote references exactly one candidate (M:1)
- **Constraint**: One user can vote only once per post

---

## 4. API Specification

### 4.1 Authentication Endpoints

#### POST `/auth/signup`
**Request Body**:
```json
{
  "name": "string",
  "email": "string",
  "password": "string"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "created_at": "timestamp"
}
```

---

#### POST `/auth/login`
**Request Body**:
```json
{
  "email": "string",
  "password": "string"
}
```

**Response**: `200 OK`
```json
{
  "access_token": "jwt_string",
  "refresh_token": "jwt_string",
  "token_type": "bearer"
}
```

---

#### POST `/auth/refresh`
**Request Body**:
```json
{
  "refresh_token": "jwt_string"
}
```

**Response**: `200 OK`
```json
{
  "access_token": "jwt_string",
  "token_type": "bearer"
}
```

---

### 4.2 Election Endpoints

#### POST `/elections`
**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "title": "string",
  "description": "string",
  "visibility": "public|private",
  "start_time": "ISO 8601 datetime",
  "end_time": "ISO 8601 datetime"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "title": "string",
  "description": "string",
  "visibility": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "shareable_link": "url",
  "created_at": "timestamp"
}
```

---

#### GET `/elections`
**Headers**: `Authorization: Bearer {access_token}`

**Query Parameters** (optional):
- `owned_by_me`: boolean (filter to show only user's elections)

**Response**: `200 OK`
```json
{
  "elections": [
    {
      "id": "uuid",
      "title": "string",
      "visibility": "string",
      "start_time": "datetime",
      "end_time": "datetime"
    }
  ]
}
```

---

#### GET `/elections/{id}`
**Headers**: `Authorization: Bearer {access_token}` (if private)

**Response**: `200 OK`
```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "title": "string",
  "description": "string",
  "visibility": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "created_at": "timestamp"
}
```

---

#### DELETE `/elections/{id}`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only owner can delete

**Response**: `204 No Content`

---

### 4.3 Posts Endpoints

#### POST `/elections/{election_id}/posts`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only election owner

**Request Body**:
```json
{
  "title": "string"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "election_id": "uuid",
  "title": "string"
}
```

---

#### GET `/elections/{election_id}/posts`
**Response**: `200 OK`
```json
{
  "posts": [
    {
      "id": "uuid",
      "title": "string"
    }
  ]
}
```

---

### 4.4 Candidates Endpoints

#### POST `/posts/{post_id}/candidates`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only election owner

**Request Body** (multipart/form-data):
```
name: string
bio: string
image: file
```

**System Process**:
1. Upload image to Cloudinary
2. Get image_url from Cloudinary
3. Save candidate with image_url

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "post_id": "uuid",
  "name": "string",
  "bio": "string",
  "image_url": "cloudinary_url"
}
```

---

#### GET `/posts/{post_id}/candidates`
**Response**: `200 OK`
```json
{
  "candidates": [
    {
      "id": "uuid",
      "name": "string",
      "bio": "string",
      "image_url": "string"
    }
  ]
}
```

---

### 4.5 Voting Endpoints

#### POST `/votes`
**Headers**: `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "election_id": "uuid",
  "post_id": "uuid",
  "candidate_id": "uuid"
}
```

**Validation Checks**:
1. Election is active (current time between start_time and end_time)
2. User has not already voted for this post
3. If private election, user is allowed to vote

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "election_id": "uuid",
  "post_id": "uuid",
  "candidate_id": "uuid",
  "timestamp": "datetime"
}
```

**Error Responses**:
- `400 Bad Request` - "Election not active"
- `409 Conflict` - "You have already voted for this post"
- `403 Forbidden` - "You are not allowed to vote in this election"

---

#### GET `/elections/{election_id}/results`
**Response**: `200 OK`

See section 2.4 for detailed response structure

---

### 4.6 Export Endpoints

#### GET `/elections/{election_id}/download/pdf`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only owner

**Response**: Binary PDF file

---

#### GET `/elections/{election_id}/download/csv`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only owner

**Response**: CSV file

---

#### GET `/elections/{election_id}/download/excel`
**Headers**: `Authorization: Bearer {access_token}`

**Access Control**: Only owner

**Response**: Excel file (.xlsx)

---

## 5. Security Requirements

### 5.1 Authentication
- Use JWT for authentication
- Access token: 15-30 minutes expiry
- Refresh token: 7-30 days expiry
- Hash passwords using bcrypt or argon2

### 5.2 Vote Integrity
- Database constraint: `UNIQUE (user_id, post_id)` prevents duplicate voting
- Elections cannot be modified after voting starts
- Vote timestamps are immutable
- Results do NOT expose individual voter identities

### 5.3 Access Control
- Only election owners can:
  - Add/edit posts
  - Add/edit candidates
  - Delete elections
  - View dashboard
  - Download exports
- Private elections: Implement allowed_voters check (optional extension)

### 5.4 Data Protection
- Never expose password hashes in API responses
- Use foreign key constraints with `ON DELETE CASCADE`
- Validate all inputs server-side
- Sanitize user-generated content (titles, descriptions, bios)

---

## 6. Backend Architecture

### 6.1 Recommended Project Structure
```
src/
├── api/
│   └── v1/
│       ├── auth/
│       │   └── routes.py
│       ├── elections/
│       │   └── routes.py
│       ├── posts/
│       │   └── routes.py
│       ├── candidates/
│       │   └── routes.py
│       └── votes/
│           └── routes.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── jwt.py
│   └── cloudinary.py
├── services/
│   ├── auth_service.py
│   ├── election_service.py
│   ├── vote_service.py
│   └── candidate_service.py
├── models/
│   ├── user.py
│   ├── election.py
│   ├── post.py
│   ├── candidate.py
│   └── vote.py
├── schemas/
│   ├── user.py
│   ├── election.py
│   ├── post.py
│   ├── candidate.py
│   └── vote.py
├── utils/
│   ├── pdf_exporter.py
│   ├── excel_exporter.py
│   └── csv_exporter.py
├── db/
│   ├── database.py
│   └── session.py
└── main.py
```

### 6.2 Key Components

#### Models (SQLAlchemy/SQLModel)
Define database tables as Python classes

#### Schemas (Pydantic)
Define request/response validation models

#### Services
Business logic layer between routes and database

#### Routes
API endpoint definitions

#### Core
Configuration, authentication, external integrations (Cloudinary)

#### Utils
Helper functions for exports, file handling, etc.

---

## 7. Third-Party Integrations

### 7.1 Supabase (PostgreSQL)
- **Purpose**: Primary database
- **Connection**: Use asyncpg or SQLAlchemy with PostgreSQL driver
- **Setup**: Get connection string from Supabase dashboard
- **Migration**: Use Alembic for database migrations

### 7.2 Cloudinary
- **Purpose**: Image hosting for candidate photos
- **Features Used**:
  - Image upload API
  - Automatic image optimization
  - CDN delivery
- **Setup**: Obtain API key, API secret, cloud name
- **Free Tier**: 25GB bandwidth/month

**Why Cloudinary?**
- Fast global CDN
- Automatic image compression
- Easy upload API
- No need to manage file storage

---

## 8. Development Workflow

### Phase 1: Setup & Auth
1. Setup FastAPI project
2. Connect to Supabase PostgreSQL
3. Create database models (SQLAlchemy/SQLModel)
4. Setup Alembic for migrations
5. Implement user signup
6. Implement user login
7. Implement JWT token generation and validation
8. Implement token refresh

### Phase 2: Elections
1. Create election endpoint
2. List elections endpoint
3. Get single election endpoint
4. Delete election endpoint
5. Add owner authorization checks

### Phase 3: Posts & Candidates
1. Add posts to election
2. Get posts for election
3. Integrate Cloudinary SDK
4. Add candidates with image upload
5. Get candidates for post

### Phase 4: Voting
1. Implement vote submission
2. Add validation checks:
   - Is election active?
   - Has user already voted?
3. Handle unique constraint violations
4. Test concurrent voting scenarios

### Phase 5: Results & Analytics
1. Build results aggregation query
2. Calculate vote counts per candidate
3. Calculate percentages
4. Implement dashboard endpoint
5. Add owner-only access control

### Phase 6: Exports
1. Implement PDF generation (use ReportLab or WeasyPrint)
2. Implement CSV export
3. Implement Excel export (use openpyxl)
4. Add owner authorization

### Phase 7: Testing & Security
1. Write unit tests for services
2. Write integration tests for API endpoints
3. Security audit
4. Load testing for concurrent votes
5. Fix bugs and edge cases

### Phase 8: Deployment
1. Setup production database on Supabase
2. Deploy backend to Render/Fly.io/Railway
3. Configure Cloudinary production credentials
4. Setup environment variables
5. Monitor and maintain

---

## 9. Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes
- `UNAUTHORIZED` - Missing or invalid token
- `FORBIDDEN` - User doesn't have permission
- `NOT_FOUND` - Resource doesn't exist
- `CONFLICT` - Duplicate vote or unique constraint violation
- `VALIDATION_ERROR` - Invalid input data
- `ELECTION_NOT_ACTIVE` - Voting outside time window
- `ALREADY_VOTED` - User already voted for this post

---

## 10. Testing Requirements

### Unit Tests
- Services layer functions
- Vote validation logic
- JWT token generation/validation
- Export generators

### Integration Tests
- Full API endpoint workflows
- Database transactions
- Authentication flows

### Load Tests
- Concurrent vote submissions
- Results endpoint under load
- Database query performance

---

## 11. Deployment Checklist

### Environment Variables
```
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### Production Considerations
- Enable HTTPS only
- Setup CORS properly
- Rate limiting on authentication endpoints
- Database connection pooling
- Log aggregation
- Error monitoring (Sentry)
- Regular database backups

---

## 12. Success Metrics

### Technical Metrics
- API response time < 200ms (p95)
- 99.9% uptime
- Zero duplicate votes
- Zero data loss

### User Metrics
- Election creation success rate
- Vote submission success rate
- Export download success rate

---

## 13. Optional Extensions (Future Phases)

These are NOT required for MVP but documented for future reference:

### Private Elections
Add `allowed_voters` table:
```sql
id                UUID PRIMARY KEY
election_id       UUID REFERENCES elections(id)
email             TEXT
```

Check if voter is in allowed list before accepting votes

### Audit Logs
Track all actions in `audit_logs` table for transparency

### Vote Change
Allow users to change their vote within time window (requires removing unique constraint, adding timestamp ordering)

---

## 14. Glossary

- **Election**: A voting event with a defined time period
- **Post**: A position/role being voted on (e.g., President)
- **Candidate**: A person running for a specific post
- **Vote**: A single user's choice for one candidate in one post
- **Owner**: User who created the election
- **Voter**: User who casts votes in an election

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 17, 2025 | Initial PRD |

---

**END OF DOCUMENT**