import { useState } from "react";
import {
  ArrowLeft,
  CreditCard,
  Lock,
  Calendar,
  Users,
  Star,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  formatCurrency,
  formatDateRange,
  calculateNights,
  generateBookingRef,
} from "@/lib/utils";
import { getListingById } from "@/data/mockListings";
import type { PricingBreakdown, BookingConfirmation } from "@/types";

interface CheckoutPageProps {
  listingId: string;
  checkIn: Date;
  checkOut: Date;
  guests: number;
  pricing: PricingBreakdown;
  onBack: () => void;
  onComplete: (confirmation: BookingConfirmation) => void;
}

export function CheckoutPage({
  listingId,
  checkIn,
  checkOut,
  guests,
  pricing,
  onBack,
  onComplete,
}: CheckoutPageProps) {
  const listing = getListingById(listingId);
  const [guestName, setGuestName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [guestPhone, setGuestPhone] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvc, setCardCvc] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (!listing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-4">Listing not found</h2>
          <Button onClick={onBack}>Go back</Button>
        </Card>
      </div>
    );
  }

  const nights = calculateNights(checkIn, checkOut);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!guestName.trim()) {
      newErrors.guestName = "Name is required";
    }

    if (!guestEmail.trim()) {
      newErrors.guestEmail = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(guestEmail)) {
      newErrors.guestEmail = "Invalid email address";
    }

    if (!cardNumber.trim() || cardNumber.replace(/\s/g, "").length < 16) {
      newErrors.cardNumber = "Valid card number is required";
    }

    if (!cardExpiry.trim() || !/^\d{2}\/\d{2}$/.test(cardExpiry)) {
      newErrors.cardExpiry = "Valid expiry (MM/YY) is required";
    }

    if (!cardCvc.trim() || cardCvc.length < 3) {
      newErrors.cardCvc = "Valid CVC is required";
    }

    if (!agreeTerms) {
      newErrors.agreeTerms = "You must agree to the terms";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsProcessing(true);

    // Simulate payment processing
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const confirmation: BookingConfirmation = {
      bookingRef: generateBookingRef(),
      listing,
      checkIn,
      checkOut,
      guests,
      pricing,
      guestName,
      guestEmail,
      bookedAt: new Date(),
    };

    onComplete(confirmation);
  };

  const formatCardNumber = (value: string) => {
    const digits = value.replace(/\D/g, "").substring(0, 16);
    return digits.replace(/(\d{4})(?=\d)/g, "$1 ");
  };

  const formatExpiry = (value: string) => {
    const digits = value.replace(/\D/g, "").substring(0, 4);
    if (digits.length >= 2) {
      return digits.substring(0, 2) + "/" + digits.substring(2);
    }
    return digits;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={onBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Confirm and pay</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Forms */}
          <div className="space-y-6">
            {/* Trip Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Your trip</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-medium">Dates</p>
                    <p className="text-muted-foreground">
                      {formatDateRange(checkIn, checkOut)}
                    </p>
                  </div>
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-medium">Guests</p>
                    <p className="text-muted-foreground">
                      {guests} guest{guests > 1 ? "s" : ""}
                    </p>
                  </div>
                  <Users className="h-5 w-5 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            {/* Guest Information */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Guest information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full name *</label>
                  <Input
                    placeholder="John Doe"
                    value={guestName}
                    onChange={(e) => setGuestName(e.target.value)}
                    className={errors.guestName ? "border-red-500" : ""}
                  />
                  {errors.guestName && (
                    <p className="text-xs text-red-500">{errors.guestName}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email *</label>
                  <Input
                    type="email"
                    placeholder="john@example.com"
                    value={guestEmail}
                    onChange={(e) => setGuestEmail(e.target.value)}
                    className={errors.guestEmail ? "border-red-500" : ""}
                  />
                  {errors.guestEmail && (
                    <p className="text-xs text-red-500">{errors.guestEmail}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Phone (optional)
                  </label>
                  <Input
                    type="tel"
                    placeholder="+1 (555) 123-4567"
                    value={guestPhone}
                    onChange={(e) => setGuestPhone(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Payment */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Pay with card
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Card number</label>
                  <Input
                    placeholder="4242 4242 4242 4242"
                    value={cardNumber}
                    onChange={(e) =>
                      setCardNumber(formatCardNumber(e.target.value))
                    }
                    className={errors.cardNumber ? "border-red-500" : ""}
                  />
                  {errors.cardNumber && (
                    <p className="text-xs text-red-500">{errors.cardNumber}</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Expiry</label>
                    <Input
                      placeholder="MM/YY"
                      value={cardExpiry}
                      onChange={(e) =>
                        setCardExpiry(formatExpiry(e.target.value))
                      }
                      className={errors.cardExpiry ? "border-red-500" : ""}
                    />
                    {errors.cardExpiry && (
                      <p className="text-xs text-red-500">{errors.cardExpiry}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">CVC</label>
                    <Input
                      placeholder="123"
                      value={cardCvc}
                      onChange={(e) =>
                        setCardCvc(e.target.value.replace(/\D/g, "").substring(0, 4))
                      }
                      className={errors.cardCvc ? "border-red-500" : ""}
                    />
                    {errors.cardCvc && (
                      <p className="text-xs text-red-500">{errors.cardCvc}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Lock className="h-4 w-4" />
                  Your payment info is encrypted and secure
                </div>
              </CardContent>
            </Card>

            {/* Terms */}
            <Card>
              <CardContent className="pt-6">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="mt-1"
                  />
                  <span className="text-sm text-muted-foreground">
                    I agree to the{" "}
                    <span className="text-primary underline">House Rules</span>,{" "}
                    <span className="text-primary underline">
                      Cancellation Policy
                    </span>
                    , and{" "}
                    <span className="text-primary underline">
                      StayFinder Terms of Service
                    </span>
                    .
                  </span>
                </label>
                {errors.agreeTerms && (
                  <p className="text-xs text-red-500 mt-2">{errors.agreeTerms}</p>
                )}
              </CardContent>
            </Card>

            {/* Submit Button */}
            <Button
              className="w-full h-12 text-lg"
              onClick={handleSubmit}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  Processing...
                </>
              ) : (
                <>
                  <Lock className="h-4 w-4 mr-2" />
                  Confirm and pay {formatCurrency(pricing.total)}
                </>
              )}
            </Button>
          </div>

          {/* Right Column - Summary */}
          <div>
            <Card className="sticky top-4">
              <CardContent className="p-6">
                {/* Listing preview */}
                <div className="flex gap-4 pb-6 border-b">
                  <img
                    src={listing.images[0]}
                    alt={listing.title}
                    className="w-32 h-24 object-cover rounded-lg"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-muted-foreground capitalize">
                      {listing.propertyType} in {listing.location.city}
                    </p>
                    <p className="font-medium truncate">{listing.title}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                      <span className="text-sm font-semibold">
                        {listing.rating}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        ({listing.reviewCount} reviews)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Price breakdown */}
                <div className="py-6 border-b space-y-3">
                  <h3 className="font-semibold">Price details</h3>
                  <div className="flex justify-between text-sm">
                    <span>
                      {formatCurrency(pricing.nightlyRate)} × {pricing.nights}{" "}
                      night{pricing.nights > 1 ? "s" : ""}
                    </span>
                    <span>{formatCurrency(pricing.subtotal)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Cleaning fee</span>
                    <span>{formatCurrency(pricing.cleaningFee)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Service fee</span>
                    <span>{formatCurrency(pricing.serviceFee)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Taxes</span>
                    <span>{formatCurrency(pricing.taxes)}</span>
                  </div>
                </div>

                {/* Total */}
                <div className="pt-6 flex justify-between font-semibold text-lg">
                  <span>Total (USD)</span>
                  <span>{formatCurrency(pricing.total)}</span>
                </div>

                {/* Cancellation badge */}
                <div className="mt-6 flex items-center gap-2">
                  <Badge variant="secondary" className="capitalize">
                    {listing.cancellationPolicy} cancellation
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

