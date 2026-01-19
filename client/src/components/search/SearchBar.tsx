import { useState } from "react";
import { Search, MapPin, Calendar, Users, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import type { SearchFilters } from "@/types";

interface SearchBarProps {
  onSearch: (filters: SearchFilters) => void;
  initialFilters?: Partial<SearchFilters>;
  compact?: boolean;
}

export function SearchBar({
  onSearch,
  initialFilters,
  compact = false,
}: SearchBarProps) {
  const [location, setLocation] = useState(initialFilters?.location || "");
  const [checkIn, setCheckIn] = useState<string>("");
  const [checkOut, setCheckOut] = useState<string>("");
  const [guests, setGuests] = useState(initialFilters?.guests || 1);
  const [naturalQuery, setNaturalQuery] = useState("");
  const [useNaturalLanguage, setUseNaturalLanguage] = useState(false);

  const handleSearch = () => {
    if (useNaturalLanguage && naturalQuery) {
      // Parse natural language query (simplified for demo)
      const parsed = parseNaturalQuery(naturalQuery);
      onSearch(parsed);
    } else {
      onSearch({
        location,
        checkIn: checkIn ? new Date(checkIn) : null,
        checkOut: checkOut ? new Date(checkOut) : null,
        guests,
      });
    }
  };

  const parseNaturalQuery = (query: string): SearchFilters => {
    // Simple keyword extraction for demo
    const lowerQuery = query.toLowerCase();
    let extractedLocation = "";
    let extractedGuests = 2;
    let priceMax: number | undefined;

    // Extract location hints
    const cities = [
      "lake tahoe",
      "austin",
      "san diego",
      "boston",
      "miami",
      "fredericksburg",
    ];
    for (const city of cities) {
      if (lowerQuery.includes(city)) {
        extractedLocation = city;
        break;
      }
    }

    // Extract guest count
    const guestMatch = lowerQuery.match(/(\d+)\s*(?:people|guests|person)/);
    if (guestMatch) {
      extractedGuests = parseInt(guestMatch[1]);
    }

    // Extract price
    const priceMatch = lowerQuery.match(
      /under\s*\$?(\d+)|less\s*than\s*\$?(\d+)|\$(\d+)\s*(?:per|\/)\s*night/
    );
    if (priceMatch) {
      priceMax = parseInt(priceMatch[1] || priceMatch[2] || priceMatch[3]);
    }

    return {
      location: extractedLocation,
      checkIn: null,
      checkOut: null,
      guests: extractedGuests,
      priceMax,
    };
  };

  if (compact) {
    return (
      <Card className="p-2 flex items-center gap-2 shadow-lg border-2">
        <div className="flex items-center gap-2 px-3 flex-1">
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Where to?"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="border-0 p-0 h-8 focus-visible:ring-0"
          />
        </div>
        <div className="h-6 w-px bg-border" />
        <div className="flex items-center gap-2 px-3">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Any dates</span>
        </div>
        <div className="h-6 w-px bg-border" />
        <div className="flex items-center gap-2 px-3">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">{guests} guests</span>
        </div>
        <Button size="icon" onClick={handleSearch} className="rounded-full">
          <Search className="h-4 w-4" />
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toggle for search mode */}
      <div className="flex justify-center gap-2">
        <Button
          variant={!useNaturalLanguage ? "default" : "outline"}
          size="sm"
          onClick={() => setUseNaturalLanguage(false)}
        >
          <Search className="h-4 w-4 mr-2" />
          Structured Search
        </Button>
        <Button
          variant={useNaturalLanguage ? "default" : "outline"}
          size="sm"
          onClick={() => setUseNaturalLanguage(true)}
        >
          <Sparkles className="h-4 w-4 mr-2" />
          Natural Language
        </Button>
      </div>

      {useNaturalLanguage ? (
        <Card className="p-4 shadow-xl border-2">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-amber-500 mt-2" />
              <Input
                placeholder='Try: "Cozy cabin near Lake Tahoe for 4 people this weekend under $300/night"'
                value={naturalQuery}
                onChange={(e) => setNaturalQuery(e.target.value)}
                className="text-base h-12"
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
            </div>
            <div className="flex justify-end">
              <Button onClick={handleSearch} size="lg" className="px-8">
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-4 shadow-xl border-2">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Location */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Location
              </label>
              <Input
                placeholder="Where are you going?"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>

            {/* Check-in */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Check-in
              </label>
              <Input
                type="date"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
                min={new Date().toISOString().split("T")[0]}
              />
            </div>

            {/* Check-out */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Check-out
              </label>
              <Input
                type="date"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
                min={checkIn || new Date().toISOString().split("T")[0]}
              />
            </div>

            {/* Guests */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Guests
              </label>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setGuests(Math.max(1, guests - 1))}
                  disabled={guests <= 1}
                >
                  -
                </Button>
                <span className="w-12 text-center font-medium">{guests}</span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setGuests(guests + 1)}
                >
                  +
                </Button>
              </div>
            </div>
          </div>

          <div className="flex justify-center mt-6">
            <Button onClick={handleSearch} size="lg" className="px-12">
              <Search className="h-4 w-4 mr-2" />
              Search
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

