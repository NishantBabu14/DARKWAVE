# 🗄️ DARKWAVE Database Schema

## Overview

DARKWAVE uses a relational database to manage users, conversations, AI memory, and future intelligent features.

---

# Users

Stores user account information.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary Key |
| username | String | Unique username |
| email | String | User email |
| password_hash | String | Encrypted password |
| created_at | DateTime | Account creation time |

---

# Chat Sessions

Stores conversation sessions.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary Key |
| user_id | Integer | Linked user |
| title | String | Chat title |
| created_at | DateTime | Creation time |
| updated_at | DateTime | Last activity |

---

# Chat Messages

Stores individual messages.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary Key |
| session_id | Integer | Linked chat session |
| role | String | user / assistant / system |
| content | Text | Message content |
| tokens | Integer | Token count |
| created_at | DateTime | Timestamp |

---

# Future Tables

## AI Memory
- Long-term memory
- User preferences
- Personalized context

## Research History
- Search queries
- Sources
- Generated summaries

## Uploaded Files
- PDF
- Images
- Documents
- Metadata

## Voice History
- Speech transcripts
- Audio metadata

---

# Relationships

User
└── Chat Sessions
    └── Chat Messages

Future:

User
├── AI Memory
├── Research History
├── Uploaded Files
└── Voice History

---

# Design Goals

- Fast performance
- Secure storage
- Easy scalability
- Modular structure
- AI-ready architecture

---

🌊 **DARKWAVE Database — Built for the Future of AI**