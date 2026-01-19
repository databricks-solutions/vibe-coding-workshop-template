import { useState } from "react";
import { HomePage } from "./pages/HomePage";
import { SearchResultsPage } from "./pages/SearchResultsPage";
import { ListingDetailPage } from "./pages/ListingDetailPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { ConfirmationPage } from "./pages/ConfirmationPage";
import type {
  AppView,
  SearchFilters,
  PricingBreakdown,
  BookingConfirmation,
} from "./types";

interface BookingState {
  listingId: string;
  checkIn: Date;
  checkOut: Date;
  guests: number;
  pricing: PricingBreakdown;
}

function App() {
  const [currentView, setCurrentView] = useState<AppView>("home");
  const [searchFilters, setSearchFilters] = useState<SearchFilters>({
    location: "",
    checkIn: null,
    checkOut: null,
    guests: 2,
  });
  const [selectedListingId, setSelectedListingId] = useState<string | null>(
    null
  );
  const [bookingState, setBookingState] = useState<BookingState | null>(null);
  const [confirmation, setConfirmation] = useState<BookingConfirmation | null>(
    null
  );

  // Navigation handlers
  const handleSearch = (filters: SearchFilters) => {
    setSearchFilters(filters);
    setCurrentView("search");
  };

  const handleSelectListing = (id: string) => {
    setSelectedListingId(id);
    setCurrentView("listing");
  };

  const handleBackToHome = () => {
    setCurrentView("home");
    setSelectedListingId(null);
    setBookingState(null);
  };

  const handleBackToSearch = () => {
    setCurrentView("search");
    setSelectedListingId(null);
  };

  const handleBackToListing = () => {
    setCurrentView("listing");
    setBookingState(null);
  };

  const handleReserve = (
    listingId: string,
    checkIn: Date,
    checkOut: Date,
    guests: number,
    pricing: PricingBreakdown
  ) => {
    setBookingState({ listingId, checkIn, checkOut, guests, pricing });
    setCurrentView("checkout");
  };

  const handleBookingComplete = (bookingConfirmation: BookingConfirmation) => {
    setConfirmation(bookingConfirmation);
    setCurrentView("confirmation");
  };

  const handleNewBooking = () => {
    setCurrentView("home");
    setSearchFilters({
      location: "",
      checkIn: null,
      checkOut: null,
      guests: 2,
    });
    setSelectedListingId(null);
    setBookingState(null);
    setConfirmation(null);
  };

  // Render current view
  const renderView = () => {
    switch (currentView) {
      case "home":
        return (
          <HomePage
            onSearch={handleSearch}
            onSelectListing={handleSelectListing}
          />
        );

      case "search":
        return (
          <SearchResultsPage
            filters={searchFilters}
            onSearch={handleSearch}
            onSelectListing={handleSelectListing}
            onBack={handleBackToHome}
          />
        );

      case "listing":
        if (!selectedListingId) {
          setCurrentView("home");
          return null;
        }
        return (
          <ListingDetailPage
            listingId={selectedListingId}
            onBack={handleBackToSearch}
            onReserve={handleReserve}
          />
        );

      case "checkout":
        if (!bookingState) {
          setCurrentView("listing");
          return null;
        }
        return (
          <CheckoutPage
            listingId={bookingState.listingId}
            checkIn={bookingState.checkIn}
            checkOut={bookingState.checkOut}
            guests={bookingState.guests}
            pricing={bookingState.pricing}
            onBack={handleBackToListing}
            onComplete={handleBookingComplete}
          />
        );

      case "confirmation":
        if (!confirmation) {
          setCurrentView("home");
          return null;
        }
        return (
          <ConfirmationPage
            confirmation={confirmation}
            onNewBooking={handleNewBooking}
          />
        );

      default:
        return (
          <HomePage
            onSearch={handleSearch}
            onSelectListing={handleSelectListing}
          />
        );
    }
  };

  return <div className="min-h-screen bg-background">{renderView()}</div>;
}

export default App;
