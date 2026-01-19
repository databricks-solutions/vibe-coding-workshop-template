# StayFinder UI Design Document

**Version**: 1.0  
**Date**: January 12, 2026  
**Status**: Implemented

---

## Overview

This document describes the UI implementation for StayFinder, a consumer-facing accommodation marketplace. The design follows the happy-path user journey from the PRD, focusing on the Guest persona's primary workflow: Discovery → Search → View Details → Checkout → Confirmation.

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui (Radix primitives) |
| Icons | Lucide React |
| State Management | React useState (simple state lifting) |
| Data | Mock data (client-side) |

---

## Key Screens

### 1. Home Page (`HomePage.tsx`)

**Purpose**: Landing page with prominent search and featured listings

**Key Sections**:
- **Hero Section**: Gradient background with search bar
- **Value Props**: Transparent pricing, verified listings, secure payments
- **Featured Listings**: 3 hand-picked properties
- **Popular Destinations**: Quick-search cards for common locations

**User Actions**:
- Enter structured search (location, dates, guests)
- Use natural language search
- Click featured listing → Listing Detail
- Click destination → Search Results

```
┌─────────────────────────────────────────────┐
│              HERO + SEARCH BAR              │
│  ┌─────────────────────────────────────┐   │
│  │ Location │ Check-in │ Check-out │ 👤 │   │
│  └─────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│  💰 Transparent   🛡️ Verified   💳 Secure  │
├─────────────────────────────────────────────┤
│         FEATURED LISTINGS (3 cards)         │
│  ┌─────┐  ┌─────┐  ┌─────┐                 │
│  │     │  │     │  │     │                 │
│  └─────┘  └─────┘  └─────┘                 │
├─────────────────────────────────────────────┤
│         POPULAR DESTINATIONS                │
│  🏔️ Lake Tahoe  🎸 Austin  🏖️ San Diego   │
└─────────────────────────────────────────────┘
```

---

### 2. Search Results Page (`SearchResultsPage.tsx`)

**Purpose**: Display filterable listing results

**Key Sections**:
- **Sticky Header**: Compact search bar + filter toggle
- **Filter Panel**: Price range, amenities (collapsible)
- **Results Grid**: Listing cards with pagination
- **View Toggle**: Grid vs Map (map placeholder)

**User Actions**:
- Refine search with filters
- Toggle amenity filters
- Switch grid/map view
- Click listing → Listing Detail
- Back → Home

```
┌─────────────────────────────────────────────┐
│ ← │ [Compact Search Bar]        │ Filters │  │
├─────────────────────────────────────────────┤
│ Price: [$___] - [$___]                      │
│ Amenities: [Wifi] [Kitchen] [Pool] ...      │
├─────────────────────────────────────────────┤
│ "Stays in Lake Tahoe" - 6 properties        │
├─────────────────────────────────────────────┤
│  ┌─────┐  ┌─────┐  ┌─────┐                 │
│  │     │  │     │  │     │                 │
│  │ $245│  │ $189│  │ $495│                 │
│  └─────┘  └─────┘  └─────┘                 │
│  ┌─────┐  ┌─────┐  ┌─────┐                 │
│  │     │  │     │  │     │                 │
│  └─────┘  └─────┘  └─────┘                 │
└─────────────────────────────────────────────┘
```

---

### 3. Listing Detail Page (`ListingDetailPage.tsx`)

**Purpose**: Full property details with booking capability

**Key Sections**:
- **Image Gallery**: 4-image grid with lightbox
- **Property Info**: Title, rating, location, host
- **Description**: Full property description
- **Amenities**: Categorized list with checkmarks
- **House Rules**: Check-in/out times, policies
- **Reviews**: Recent reviews with ratings
- **Cancellation Policy**: Policy details
- **Booking Widget**: Sticky sidebar with date picker, pricing

**User Actions**:
- Browse photos (lightbox)
- Select dates and guests
- View pricing breakdown
- Reserve → Checkout
- Back → Search Results

```
┌─────────────────────────────────────────────┐
│ ← Back to search                            │
├─────────────────────────────────────────────┤
│ ┌───────────────┬───────┬───────┐          │
│ │               │       │       │          │
│ │   Main Image  │ Img 2 │ Img 3 │          │
│ │               │───────│───────│          │
│ │               │ Img 4 │ Img 5 │          │
│ └───────────────┴───────┴───────┘          │
├───────────────────────────┬─────────────────┤
│ Cozy Mountain Cabin       │ ┌─────────────┐ │
│ ⭐ 4.92 · Superhost       │ │ $245/night  │ │
│ 📍 Tahoe City, CA         │ │             │ │
│                           │ │ Check-in    │ │
│ ─────────────────         │ │ [  date  ]  │ │
│ 🏠 Cabin · 6 guests       │ │ Check-out   │ │
│ 2 bedrooms · 2 baths      │ │ [  date  ]  │ │
│                           │ │             │ │
│ About this place          │ │ Guests: 2   │ │
│ Lorem ipsum dolor...      │ │             │ │
│                           │ │ [Reserve]   │ │
│ Amenities                 │ │             │ │
│ ✓ Wifi  ✓ Kitchen        │ │ $245 × 3    │ │
│ ✓ Hot tub ✓ Fireplace    │ │ Cleaning    │ │
│                           │ │ Service fee │ │
│ House Rules               │ │ Taxes       │ │
│ Check-in: 3:00 PM        │ │ ───────     │ │
│ Check-out: 11:00 AM      │ │ Total: $XXX │ │
│                           │ └─────────────┘ │
│ Reviews                   │                 │
│ ⭐ 4.92 · 128 reviews    │                 │
└───────────────────────────┴─────────────────┘
```

---

### 4. Checkout Page (`CheckoutPage.tsx`)

**Purpose**: Collect guest info and payment

**Key Sections**:
- **Trip Summary**: Dates and guest count
- **Guest Information**: Name, email, phone (optional)
- **Payment Form**: Card number, expiry, CVC
- **Terms Checkbox**: Policy agreement
- **Booking Summary**: Property preview, price breakdown

**User Actions**:
- Enter guest details
- Enter payment info
- Accept terms
- Confirm and pay → Confirmation
- Back → Listing Detail

```
┌─────────────────────────────────────────────┐
│ ← Back                                      │
├─────────────────────────────────────────────┤
│ Confirm and pay                             │
├───────────────────────────┬─────────────────┤
│                           │ ┌─────────────┐ │
│ Your Trip                 │ │ [img] Title │ │
│ ├─ Dates: Jan 15-18      │ │ ⭐ 4.92     │ │
│ └─ Guests: 2             │ │             │ │
│                           │ │ Price detail│ │
│ Guest Information         │ │ $245 × 3   │ │
│ ├─ Full name: [______]   │ │ Cleaning    │ │
│ ├─ Email: [______]       │ │ Service fee │ │
│ └─ Phone: [______]       │ │ Taxes       │ │
│                           │ │ ───────     │ │
│ Payment                   │ │ Total: $XXX │ │
│ ├─ Card: [4242...]       │ │             │ │
│ ├─ Expiry: [MM/YY]       │ │ Moderate    │ │
│ └─ CVC: [___]            │ │ cancellation│ │
│                           │ └─────────────┘ │
│ ☑ I agree to terms       │                 │
│                           │                 │
│ [🔒 Confirm and pay $XXX] │                 │
└───────────────────────────┴─────────────────┘
```

---

### 5. Confirmation Page (`ConfirmationPage.tsx`)

**Purpose**: Booking success with details and next steps

**Key Sections**:
- **Success Header**: Green banner with checkmark
- **Booking Reference**: Unique confirmation code
- **Email Notice**: Confirmation sent notification
- **Reservation Details**: Property, dates, guests
- **Location & Contact**: Address (placeholder), host info
- **Payment Summary**: Final breakdown
- **Guest Details**: Name and email
- **Cancellation Policy**: Reminder
- **Actions**: Print, Book Another

**User Actions**:
- Print confirmation
- Book another stay → Home

```
┌─────────────────────────────────────────────┐
│          ✓ Booking Confirmed!               │
│      Confirmation #SF-ABCD1234              │
├─────────────────────────────────────────────┤
│ 📧 Confirmation sent to john@example.com   │
├─────────────────────────────────────────────┤
│ Your Reservation                            │
│ ┌─────┐ Cozy Mountain Cabin                │
│ │ img │ Cabin in Lake Tahoe                │
│ └─────┘ Jan 15 (3PM) → Jan 18 (11AM)       │
│         2 guests · 3 nights                 │
├─────────────────────────────────────────────┤
│ 📍 Location        │ 📞 Host Contact       │
│ Tahoe City, CA     │ Sarah (Superhost)     │
│ Address via email  │ 98% response rate     │
├─────────────────────────────────────────────┤
│ Payment Summary                             │
│ $245 × 3 nights ............... $735       │
│ Cleaning fee .................. $85        │
│ Service fee ................... $45        │
│ Taxes ......................... $86        │
│ ───────────────────────────────────        │
│ Total paid .................... $951       │
├─────────────────────────────────────────────┤
│ [🖨️ Print]        [Book Another Stay →]    │
└─────────────────────────────────────────────┘
```

---

## Core Components

### Shared UI Components (from shadcn/ui)

| Component | Location | Usage |
|-----------|----------|-------|
| Button | `components/ui/button.tsx` | Primary actions, navigation |
| Card | `components/ui/card.tsx` | Content containers |
| Input | `components/ui/input.tsx` | Form fields |
| Badge | `components/ui/badge.tsx` | Tags, status indicators |

### Custom Components

| Component | Location | Purpose |
|-----------|----------|---------|
| SearchBar | `components/search/SearchBar.tsx` | Structured and NL search input |
| ListingCard | `components/listings/ListingCard.tsx` | Property card for grids |
| BookingWidget | `components/booking/BookingWidget.tsx` | Date selection and pricing |

---

## Navigation Flow

```
                    ┌──────────┐
                    │   Home   │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        ┌──────────┐         ┌──────────┐
        │  Search  │◄────────│ Featured │
        │ Results  │         │ Listing  │
        └────┬─────┘         └────┬─────┘
             │                    │
             └────────┬───────────┘
                      │
                      ▼
               ┌──────────┐
               │ Listing  │
               │  Detail  │
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐
               │ Checkout │
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐
               │  Confirm │
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐
               │   Home   │ (New booking)
               └──────────┘
```

---

## State Management

Simple state lifting with React useState in `App.tsx`:

```typescript
interface AppState {
  currentView: "home" | "search" | "listing" | "checkout" | "confirmation";
  searchFilters: SearchFilters;
  selectedListingId: string | null;
  bookingState: BookingState | null;
  confirmation: BookingConfirmation | null;
}
```

No external state management libraries needed for this MVP.

---

## Data Flow

1. **Mock Data** (`data/mockListings.ts`): 6 sample listings with full details
2. **Search**: Client-side filtering by location, guests, price
3. **Booking Flow**: State passed through props between pages
4. **No API calls**: All data client-side for simplicity

---

## Design Tokens

### Colors (CSS Variables)

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | Rose 500 (`350 89% 60%`) | Buttons, links, accents |
| `--accent` | Rose 50 | Hover states, highlights |
| `--destructive` | Red 500 | Error states |
| `--muted-foreground` | Gray 500 | Secondary text |

### Typography

- **Headings**: font-bold, text-xl to text-4xl
- **Body**: text-base, text-muted-foreground for secondary
- **Labels**: text-sm font-medium

### Spacing

- **Container**: max-w-screen, px-4
- **Cards**: p-4 to p-6
- **Sections**: py-8 to py-16

---

## Responsive Behavior

| Breakpoint | Layout Changes |
|------------|----------------|
| Mobile (< 768px) | Single column, stacked cards |
| Tablet (768px+) | 2-column grids |
| Desktop (1024px+) | 3-column grids, side-by-side layouts |

---

## Accessibility Notes

- All interactive elements are keyboard accessible
- Form inputs have associated labels
- Color contrast meets WCAG AA standards
- Images have alt text
- Focus states visible on all interactive elements

---

## Future Enhancements (Not Implemented)

- [ ] Interactive map view with Mapbox/Google Maps
- [ ] Date range picker with calendar component
- [ ] Real Stripe Elements integration
- [ ] URL-based routing with React Router
- [ ] Persistent state with localStorage
- [ ] Real API integration

---

## File Structure

```
client/src/
├── App.tsx                    # Main app with state management
├── index.css                  # Tailwind + custom styles
├── main.tsx                   # React entry point
│
├── types/
│   └── index.ts               # TypeScript interfaces
│
├── lib/
│   └── utils.ts               # Helper functions (cn, formatters)
│
├── data/
│   └── mockListings.ts        # Sample data
│
├── components/
│   ├── ui/                    # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── badge.tsx
│   │
│   ├── search/
│   │   └── SearchBar.tsx      # Search input component
│   │
│   ├── listings/
│   │   └── ListingCard.tsx    # Property card
│   │
│   └── booking/
│       └── BookingWidget.tsx  # Booking sidebar
│
└── pages/
    ├── HomePage.tsx           # Landing page
    ├── SearchResultsPage.tsx  # Search results
    ├── ListingDetailPage.tsx  # Property detail
    ├── CheckoutPage.tsx       # Payment form
    └── ConfirmationPage.tsx   # Success page
```

---

*Document maintained by Engineering Team. Last updated: January 12, 2026*

