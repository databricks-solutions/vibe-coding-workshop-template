// Core domain types for StayFinder

export interface Listing {
  id: string;
  title: string;
  description: string;
  location: {
    city: string;
    state: string;
    neighborhood: string;
    coordinates: { lat: number; lng: number };
  };
  propertyType: "house" | "apartment" | "cabin" | "condo" | "villa";
  images: string[];
  pricePerNight: number;
  cleaningFee: number;
  serviceFee: number;
  taxRate: number;
  maxGuests: number;
  bedrooms: number;
  beds: number;
  bathrooms: number;
  amenities: string[];
  rating: number;
  reviewCount: number;
  host: {
    name: string;
    responseRate: number;
    superhost: boolean;
  };
  houseRules: {
    checkIn: string;
    checkOut: string;
    policies: string[];
  };
  cancellationPolicy: "flexible" | "moderate" | "strict";
}

export interface Review {
  id: string;
  author: string;
  date: string;
  rating: number;
  comment: string;
}

export interface SearchFilters {
  location: string;
  checkIn: Date | null;
  checkOut: Date | null;
  guests: number;
  priceMin?: number;
  priceMax?: number;
  propertyType?: string[];
  amenities?: string[];
}

export interface BookingDetails {
  listingId: string;
  checkIn: Date;
  checkOut: Date;
  guests: number;
  guestName: string;
  guestEmail: string;
  guestPhone?: string;
}

export interface PricingBreakdown {
  nightlyRate: number;
  nights: number;
  subtotal: number;
  cleaningFee: number;
  serviceFee: number;
  taxes: number;
  total: number;
}

export interface BookingConfirmation {
  bookingRef: string;
  listing: Listing;
  checkIn: Date;
  checkOut: Date;
  guests: number;
  pricing: PricingBreakdown;
  guestName: string;
  guestEmail: string;
  bookedAt: Date;
}

export type AppView =
  | "home"
  | "search"
  | "listing"
  | "checkout"
  | "confirmation";

export interface AppState {
  currentView: AppView;
  searchFilters: SearchFilters;
  selectedListingId: string | null;
  bookingDetails: BookingDetails | null;
  bookingConfirmation: BookingConfirmation | null;
}

