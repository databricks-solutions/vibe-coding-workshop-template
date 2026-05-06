## IMPORTANT - READ FIRST
Your ONLY task is to create a PRD document. Do NOT:
- Generate any code or scripts
- Create any implementation files
- Start building the application
- Define table structures, schemas, or database designs
- Create table names or data models
- Define API endpoints, routes, or API specifications
- Include implementation-specific logic or technical details
- Do anything other than creating the PRD

You MUST:
- Create ONLY the PRD document
- Save it to: docs/design_prd.md
- STOP after saving the PRD - do nothing else

---

# Product Requirements Document Request

Please create a simple, focused Product Requirements Document (PRD) for a consumer marketplace booking application.

## Application Overview

Create a PRD for a **consumer-facing marketplace** that connects Guests/Customers with Hosts/Providers to discover, search, and book accommodations - similar to Airbnb.

**Key Context:**
- **Industry**: Sample for Enablement
- **Use Case**: Booking App
- **Product Name**: **StayFindr** — use this name consistently throughout the PRD and all generated artifacts (UI, components, mock data, coupon codes, agent greetings, etc.)
- **Target Market**: US listings with USD currency only
- **Access Model**: Open, public site (no user registration or login required)
- Web-first design with mobile considerations

## Core Personas

Focus on these two primary personas:

1. **Guest/Customer**: End users who search, compare, book, and pay for accommodations
2. **Host/Provider**: Businesses or individuals who list offerings, manage availability, and fulfill bookings

## Core Features to Document

### Three Distinct Search Experiences

The PRD must describe three different search types:

**1. Standard Search (Structured Filters)**
- Traditional filter-based search with explicit user selections
- Filters: location/destination, check-in/check-out dates, number of guests, price range, amenities, property type
- Date validation: check-in must not be in the past, check-out must be after check-in. When check-in changes to a date on or after check-out, auto-advance check-out to the next day
- Results page with ranking, listing cards, map synchronization, filters, and pagination

**2. Natural Language Search (Text-to-Filters)**
- Free-text search that parses user queries into structured filters
- Example query: *"quiet 2-bedroom near downtown this weekend under $200/night with parking"*
- System translates natural language into filter parameters
- Combines with availability checking
- Returns same structured results as standard search

**3. Agent-Based Search (Intent & Context-Aware)**
- AI-powered search that interprets higher-level user intent
- Example query: *"I want to stay near the concert venue for the Taylor Swift show next month"*
- Agent understands context (event dates, venue location, typical needs)
- Proactively suggests options based on inferred preferences
- Uses additional contextual information to refine and rank results
- Can ask clarifying questions and iterate on search criteria

### Search Results & Listing Details
- Results page with ranking, listing cards, map integration, filters, and pagination
- Detail page with content sections, media galleries, amenities list, reviews summary

### Booking & Transactions
- All-in pricing display including taxes, fees, discounts, and coupons
- Booking form collects guest name and email (both required). If either field is empty, show inline validation messages (e.g., "Name is required", "Valid email is required") and update the confirm button text to indicate what is needed (e.g., "Enter name & email to book") — do not silently disable the button
- Booking confirmation workflow
- Booking modification capabilities

## Data Entities to Reference

Include these high-level entities in the PRD (names and relationships only - NO table definitions or schemas):

Users, Listings, Units/Rooms, Availability, Pricing, Fees/Taxes, Bookings, Payments, Refunds, Reviews, Wishlists, Messages

## Technical Considerations to Note

- Web-first with mobile considerations
- Map integration for location-based search
- Payment gateway integration (e.g., Stripe)
- AI/LLM integration for natural language and agent-based search

## Scope Constraints - CRITICAL

**Keep it simple** and focus only on the bare minimum required to support core search and booking features:

- **US listings with USD currency only**
- **No user registration, login, or user management**
- **No host management or property management features**
- **Open, public site** - anyone can search and book
- **High Value workflows only**
- **Happy Path only** - skip edge cases and error handling details
- Prioritize clarity over completeness

## PRD Structure Required

Create a PRD with the following sections:

### 1. Summary
- Product vision and value proposition
- Problem statement
- Target personas (2-3 maximum)
- Goals and non-goals

### 2. Scope
- MVP scope definition
- Clear out-of-scope items

### 3. User Journeys
- High-value end-to-end flows for primary personas
- Happy Path only - no edge cases
- Focus on the most important workflows

### 4. Functional Requirements
- Key requirements organized by feature area
- Simple acceptance criteria for each requirement
- Focus on what the system must do, not how it does it

### 5. Non-Functional Requirements
- Basic performance expectations
- Security considerations
- Accessibility notes
- Scalability considerations

### 6. High-Level Data Entities
- Entity names and their relationships
- Brief description of what each entity represents
- **DO NOT include table definitions, schemas, column names, or data types**

### 7. Release Plan
- Simple milestones from MVP to General Availability
- High-level phases with key deliverables

## Writing Guidelines

- Use clear, concise language
- Focus on user value and business outcomes
- Avoid technical implementation details
- Keep descriptions simple and readable
- Use bullet points and short paragraphs
- Include examples where helpful for clarity

---

```
Save this PRD to: docs/design_prd.md
STOP after saving. Do not generate any code, tables, APIs, or proceed with other tasks.
```
