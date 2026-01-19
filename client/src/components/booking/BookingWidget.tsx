import { useState } from "react";
import { Calendar, Users, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency, calculateNights } from "@/lib/utils";
import type { Listing, PricingBreakdown } from "@/types";

interface BookingWidgetProps {
  listing: Listing;
  onReserve: (
    checkIn: Date,
    checkOut: Date,
    guests: number,
    pricing: PricingBreakdown
  ) => void;
}

export function BookingWidget({ listing, onReserve }: BookingWidgetProps) {
  const [checkIn, setCheckIn] = useState<string>("");
  const [checkOut, setCheckOut] = useState<string>("");
  const [guests, setGuests] = useState(1);

  const calculatePricing = (): PricingBreakdown | null => {
    if (!checkIn || !checkOut) return null;

    const nights = calculateNights(new Date(checkIn), new Date(checkOut));
    if (nights <= 0) return null;

    const subtotal = listing.pricePerNight * nights;
    const taxes = (subtotal + listing.cleaningFee) * listing.taxRate;

    return {
      nightlyRate: listing.pricePerNight,
      nights,
      subtotal,
      cleaningFee: listing.cleaningFee,
      serviceFee: listing.serviceFee,
      taxes,
      total: subtotal + listing.cleaningFee + listing.serviceFee + taxes,
    };
  };

  const pricing = calculatePricing();

  const handleReserve = () => {
    if (pricing && checkIn && checkOut) {
      onReserve(new Date(checkIn), new Date(checkOut), guests, pricing);
    }
  };

  return (
    <Card className="sticky top-4 shadow-xl border-2">
      <CardHeader className="pb-4">
        <div className="flex items-baseline justify-between">
          <CardTitle className="text-2xl">
            {formatCurrency(listing.pricePerNight)}
            <span className="text-base font-normal text-muted-foreground">
              /night
            </span>
          </CardTitle>
          <div className="flex items-center gap-1 text-sm">
            <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
            <span className="font-semibold">{listing.rating}</span>
            <span className="text-muted-foreground">
              · {listing.reviewCount} reviews
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Date inputs */}
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              CHECK-IN
            </label>
            <Input
              type="date"
              value={checkIn}
              onChange={(e) => setCheckIn(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className="text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              CHECK-OUT
            </label>
            <Input
              type="date"
              value={checkOut}
              onChange={(e) => setCheckOut(e.target.value)}
              min={checkIn || new Date().toISOString().split("T")[0]}
              className="text-sm"
            />
          </div>
        </div>

        {/* Guests */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
            <Users className="h-3 w-3" />
            GUESTS
          </label>
          <div className="flex items-center justify-between border rounded-md p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setGuests(Math.max(1, guests - 1))}
              disabled={guests <= 1}
            >
              -
            </Button>
            <span className="font-medium">
              {guests} guest{guests > 1 ? "s" : ""}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setGuests(Math.min(listing.maxGuests, guests + 1))}
              disabled={guests >= listing.maxGuests}
            >
              +
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Maximum {listing.maxGuests} guests
          </p>
        </div>

        {/* Reserve button */}
        <Button
          className="w-full"
          size="lg"
          onClick={handleReserve}
          disabled={!pricing}
        >
          Reserve
        </Button>

        {!pricing && (
          <p className="text-center text-sm text-muted-foreground">
            Select dates to see pricing
          </p>
        )}

        {/* Pricing breakdown */}
        {pricing && (
          <div className="space-y-2 pt-4 border-t">
            <div className="flex justify-between text-sm">
              <span className="underline">
                {formatCurrency(pricing.nightlyRate)} × {pricing.nights} night
                {pricing.nights > 1 ? "s" : ""}
              </span>
              <span>{formatCurrency(pricing.subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="underline">Cleaning fee</span>
              <span>{formatCurrency(pricing.cleaningFee)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="underline">Service fee</span>
              <span>{formatCurrency(pricing.serviceFee)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="underline">Taxes</span>
              <span>{formatCurrency(pricing.taxes)}</span>
            </div>
            <div className="flex justify-between font-semibold pt-2 border-t">
              <span>Total</span>
              <span>{formatCurrency(pricing.total)}</span>
            </div>
          </div>
        )}

        {/* Cancellation policy */}
        <p className="text-xs text-center text-muted-foreground pt-2">
          {listing.cancellationPolicy === "flexible" &&
            "Free cancellation up to 24 hours before check-in"}
          {listing.cancellationPolicy === "moderate" &&
            "Free cancellation up to 5 days before check-in"}
          {listing.cancellationPolicy === "strict" &&
            "50% refund up to 1 week before check-in"}
        </p>
      </CardContent>
    </Card>
  );
}

