import { useState } from "react";
import { ArrowLeft, SlidersHorizontal, MapPin, Grid, Map } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SearchBar } from "@/components/search/SearchBar";
import { ListingCard } from "@/components/listings/ListingCard";
import { searchListings } from "@/data/mockListings";
import type { SearchFilters, Listing } from "@/types";

interface SearchResultsPageProps {
  filters: SearchFilters;
  onSearch: (filters: SearchFilters) => void;
  onSelectListing: (id: string) => void;
  onBack: () => void;
}

export function SearchResultsPage({
  filters,
  onSearch,
  onSelectListing,
  onBack,
}: SearchResultsPageProps) {
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>(
    filters.priceMax?.toString() || ""
  );
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "map">("grid");
  const [showFilters, setShowFilters] = useState(false);

  // Get filtered listings
  const listings = searchListings({
    location: filters.location,
    guests: filters.guests,
    priceMax: priceMax ? parseInt(priceMax) : undefined,
  });

  // Further filter by amenities
  const filteredListings = selectedAmenities.length
    ? listings.filter((listing) =>
        selectedAmenities.every((amenity) =>
          listing.amenities.includes(amenity)
        )
      )
    : listings;

  const commonAmenities = [
    "Wifi",
    "Kitchen",
    "Free parking",
    "Pool",
    "Hot tub",
    "Air conditioning",
    "Washer/Dryer",
    "Fireplace",
  ];

  const toggleAmenity = (amenity: string) => {
    setSelectedAmenities((prev) =>
      prev.includes(amenity)
        ? prev.filter((a) => a !== amenity)
        : [...prev, amenity]
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={onBack}>
              <ArrowLeft className="h-5 w-5" />
            </Button>

            <div className="flex-1 max-w-2xl">
              <SearchBar
                onSearch={onSearch}
                initialFilters={filters}
                compact
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                <SlidersHorizontal className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <div className="hidden md:flex border rounded-lg">
                <Button
                  variant={viewMode === "grid" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                  className="rounded-r-none"
                >
                  <Grid className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "map" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("map")}
                  className="rounded-l-none"
                >
                  <Map className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Filters panel */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border animate-in slide-in-from-top-2">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Price range */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Price per night</label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={priceMin}
                      onChange={(e) => setPriceMin(e.target.value)}
                      className="w-24"
                    />
                    <span className="text-muted-foreground">—</span>
                    <Input
                      type="number"
                      placeholder="Max"
                      value={priceMax}
                      onChange={(e) => setPriceMax(e.target.value)}
                      className="w-24"
                    />
                  </div>
                </div>

                {/* Amenities */}
                <div className="space-y-2 md:col-span-2">
                  <label className="text-sm font-medium">Amenities</label>
                  <div className="flex flex-wrap gap-2">
                    {commonAmenities.map((amenity) => (
                      <Badge
                        key={amenity}
                        variant={
                          selectedAmenities.includes(amenity)
                            ? "default"
                            : "outline"
                        }
                        className="cursor-pointer"
                        onClick={() => toggleAmenity(amenity)}
                      >
                        {amenity}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="container mx-auto px-4 py-8">
        {/* Results header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">
              {filters.location ? (
                <>
                  Stays in {filters.location}
                </>
              ) : (
                "All available stays"
              )}
            </h1>
            <p className="text-muted-foreground mt-1">
              {filteredListings.length} properties found
              {filters.guests > 1 && ` for ${filters.guests} guests`}
            </p>
          </div>

          {/* Active filters */}
          {(selectedAmenities.length > 0 || priceMax) && (
            <div className="flex items-center gap-2">
              {priceMax && (
                <Badge variant="secondary">
                  Under ${priceMax}/night
                  <button
                    className="ml-1 hover:text-destructive"
                    onClick={() => setPriceMax("")}
                  >
                    ×
                  </button>
                </Badge>
              )}
              {selectedAmenities.map((amenity) => (
                <Badge key={amenity} variant="secondary">
                  {amenity}
                  <button
                    className="ml-1 hover:text-destructive"
                    onClick={() => toggleAmenity(amenity)}
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </div>

        {viewMode === "grid" ? (
          <>
            {filteredListings.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredListings.map((listing) => (
                  <ListingCard
                    key={listing.id}
                    listing={listing}
                    onClick={onSelectListing}
                  />
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No results found</h3>
                <p className="text-muted-foreground mb-4">
                  Try adjusting your filters or searching a different location
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setPriceMax("");
                    setSelectedAmenities([]);
                    onSearch({
                      location: "",
                      checkIn: null,
                      checkOut: null,
                      guests: 2,
                    });
                  }}
                >
                  Clear all filters
                </Button>
              </Card>
            )}
          </>
        ) : (
          /* Map View Placeholder */
          <Card className="h-[600px] flex items-center justify-center bg-gray-100">
            <div className="text-center">
              <Map className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Map View</h3>
              <p className="text-muted-foreground">
                Interactive map coming soon
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                {filteredListings.length} listings would appear here
              </p>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

