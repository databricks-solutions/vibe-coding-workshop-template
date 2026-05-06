# StayFindr — UI Design Document

## Navigation Flow
```
Home → Search Results → Listing Detail → Booking → Confirmation
Home → AI Search → Listing Detail → Booking → Confirmation
```

## Pages
- **HomePage** — Hero search bar (3 types: filters/NL/agent), 6 featured listing cards, popular destinations
- **SearchResultsPage** — Filter sidebar (price, type, sort), listing result cards, map placeholder
- **ListingDetailPage** — Photo gallery, description, amenities pills, reviews, sticky booking card
- **BookingPage** — Trip details, coupon input (STAYFINDR10/WELCOME20/SUMMER15), payment form, pricing breakdown
- **BookingConfirmationPage** — Booking reference, listing summary, dates, total
- **AgentSearchPage** — Chat UI, keyword-matched responses (beach/mountain/city/budget/luxury/concert), inline listing cards

## Mock Data
10 US properties, 11 reviews, 3 coupon codes, calculatePricing function.

## Design
Warm earth tones — primary #c45d30, text #2d2417, bg #faf8f5. System fonts. Desktop-first. data-testid on interactive elements.
