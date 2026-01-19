import { Home, TrendingUp, Shield, CreditCard } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SearchBar } from "@/components/search/SearchBar";
import { ListingCard } from "@/components/listings/ListingCard";
import { mockListings } from "@/data/mockListings";
import type { SearchFilters } from "@/types";

interface HomePageProps {
  onSearch: (filters: SearchFilters) => void;
  onSelectListing: (id: string) => void;
}

export function HomePage({ onSearch, onSelectListing }: HomePageProps) {
  const featuredListings = mockListings.slice(0, 3);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-rose-500 via-pink-500 to-orange-400 text-white">
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative container mx-auto px-4 py-20 md:py-32">
          <div className="max-w-3xl mx-auto text-center mb-12">
            <div className="flex justify-center mb-6">
              <div className="bg-white/20 backdrop-blur-sm rounded-full p-4">
                <Home className="h-12 w-12" />
              </div>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-4 tracking-tight">
              Find your perfect stay
            </h1>
            <p className="text-xl md:text-2xl text-white/90">
              Discover unique homes and experiences around the United States
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-4xl mx-auto">
            <SearchBar onSearch={onSearch} />
          </div>
        </div>
      </div>

      {/* Value Props */}
      <div className="bg-gray-50 py-12 border-b">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex items-start gap-4">
              <div className="bg-rose-100 p-3 rounded-lg">
                <TrendingUp className="h-6 w-6 text-rose-600" />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1">Transparent Pricing</h3>
                <p className="text-muted-foreground text-sm">
                  See the total price upfront with all fees and taxes included
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="bg-rose-100 p-3 rounded-lg">
                <Shield className="h-6 w-6 text-rose-600" />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1">Verified Listings</h3>
                <p className="text-muted-foreground text-sm">
                  Every property is verified for quality and accuracy
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="bg-rose-100 p-3 rounded-lg">
                <CreditCard className="h-6 w-6 text-rose-600" />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1">Secure Payments</h3>
                <p className="text-muted-foreground text-sm">
                  Book with confidence using our secure payment system
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Featured Listings */}
      <div className="container mx-auto px-4 py-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold">Featured Stays</h2>
            <p className="text-muted-foreground mt-1">
              Hand-picked properties our guests love
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featuredListings.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              onClick={onSelectListing}
            />
          ))}
        </div>
      </div>

      {/* Destinations */}
      <div className="bg-gray-50 py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl md:text-3xl font-bold mb-8">
            Explore Popular Destinations
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: "Lake Tahoe, CA", count: 245, emoji: "🏔️" },
              { name: "Austin, TX", count: 189, emoji: "🎸" },
              { name: "San Diego, CA", count: 312, emoji: "🏖️" },
              { name: "Miami, FL", count: 428, emoji: "🌴" },
            ].map((dest) => (
              <Card
                key={dest.name}
                className="cursor-pointer hover:shadow-lg transition-shadow group"
                onClick={() =>
                  onSearch({
                    location: dest.name.split(",")[0],
                    checkIn: null,
                    checkOut: null,
                    guests: 2,
                  })
                }
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <span className="text-3xl">{dest.emoji}</span>
                  <div>
                    <p className="font-semibold group-hover:text-rose-600 transition-colors">
                      {dest.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {dest.count} properties
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© 2026 StayFinder. All rights reserved.</p>
          <p className="mt-2">
            A demo application showcasing accommodation booking workflows.
          </p>
        </div>
      </footer>
    </div>
  );
}

