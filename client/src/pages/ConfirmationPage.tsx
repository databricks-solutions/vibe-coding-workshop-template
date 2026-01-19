import {
  CheckCircle,
  Calendar,
  MapPin,
  Users,
  Phone,
  Mail,
  Clock,
  Home,
  Printer,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDate, calculateNights } from "@/lib/utils";
import type { BookingConfirmation } from "@/types";

interface ConfirmationPageProps {
  confirmation: BookingConfirmation;
  onNewBooking: () => void;
}

export function ConfirmationPage({
  confirmation,
  onNewBooking,
}: ConfirmationPageProps) {
  const { listing, checkIn, checkOut, guests, pricing, guestName, guestEmail } =
    confirmation;
  const nights = calculateNights(checkIn, checkOut);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      {/* Success Header */}
      <div className="bg-green-600 text-white py-16">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center mb-6">
            <div className="bg-white/20 rounded-full p-4">
              <CheckCircle className="h-16 w-16" />
            </div>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-2">
            Booking Confirmed!
          </h1>
          <p className="text-xl text-green-100">
            Your reservation has been successfully completed
          </p>
          <div className="mt-6">
            <Badge className="bg-white text-green-600 text-lg px-6 py-2">
              Confirmation #{confirmation.bookingRef}
            </Badge>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Confirmation sent notice */}
          <Card className="border-green-200 bg-green-50">
            <CardContent className="flex items-center gap-4 p-6">
              <Mail className="h-8 w-8 text-green-600" />
              <div>
                <p className="font-semibold">Confirmation sent!</p>
                <p className="text-muted-foreground">
                  We've sent your booking details to{" "}
                  <span className="font-medium text-foreground">
                    {guestEmail}
                  </span>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Booking Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Home className="h-5 w-5" />
                Your Reservation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-6 flex-col md:flex-row">
                <img
                  src={listing.images[0]}
                  alt={listing.title}
                  className="w-full md:w-48 h-36 object-cover rounded-lg"
                />
                <div className="flex-1 space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground capitalize">
                      {listing.propertyType} in {listing.location.city},{" "}
                      {listing.location.state}
                    </p>
                    <h3 className="text-xl font-semibold">{listing.title}</h3>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="flex items-start gap-2">
                      <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Check-in
                        </p>
                        <p className="font-medium">{formatDate(checkIn)}</p>
                        <p className="text-sm text-muted-foreground">
                          {listing.houseRules.checkIn}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Check-out
                        </p>
                        <p className="font-medium">{formatDate(checkOut)}</p>
                        <p className="text-sm text-muted-foreground">
                          {listing.houseRules.checkOut}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm text-muted-foreground">Guests</p>
                        <p className="font-medium">
                          {guests} guest{guests > 1 ? "s" : ""}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {nights} night{nights > 1 ? "s" : ""}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Location & Contact */}
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Property Location
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">
                  {listing.location.neighborhood}
                </p>
                <p className="text-muted-foreground">
                  {listing.location.city}, {listing.location.state}
                </p>
                <p className="text-sm text-muted-foreground mt-4">
                  Exact address will be provided after booking
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Phone className="h-5 w-5" />
                  Host Contact
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">{listing.host.name}</p>
                {listing.host.superhost && (
                  <Badge variant="secondary" className="mt-1">
                    ⭐ Superhost
                  </Badge>
                )}
                <p className="text-sm text-muted-foreground mt-4">
                  Response rate: {listing.host.responseRate}%
                </p>
                <p className="text-sm text-muted-foreground">
                  Contact info will be shared via email
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Payment Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Payment Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span>
                    {formatCurrency(pricing.nightlyRate)} × {pricing.nights}{" "}
                    night{pricing.nights > 1 ? "s" : ""}
                  </span>
                  <span>{formatCurrency(pricing.subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cleaning fee</span>
                  <span>{formatCurrency(pricing.cleaningFee)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Service fee</span>
                  <span>{formatCurrency(pricing.serviceFee)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Taxes</span>
                  <span>{formatCurrency(pricing.taxes)}</span>
                </div>
                <div className="flex justify-between pt-3 border-t font-semibold text-lg">
                  <span>Total paid</span>
                  <span className="text-green-600">
                    {formatCurrency(pricing.total)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Guest Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Guest Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Name</p>
                  <p className="font-medium">{guestName}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-medium">{guestEmail}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Cancellation Policy */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Cancellation Policy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge className="capitalize mb-3">
                {listing.cancellationPolicy}
              </Badge>
              <p className="text-muted-foreground">
                {listing.cancellationPolicy === "flexible" &&
                  "Free cancellation up to 24 hours before check-in. After that, cancel before check-in and get a full refund, minus the first night and service fee."}
                {listing.cancellationPolicy === "moderate" &&
                  "Free cancellation up to 5 days before check-in. After that, cancel before check-in and get a 50% refund, minus the service fee."}
                {listing.cancellationPolicy === "strict" &&
                  "Cancel up to 1 week before check-in and get a 50% refund. After that, the reservation is non-refundable."}
              </p>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <Button variant="outline" onClick={handlePrint} className="gap-2">
              <Printer className="h-4 w-4" />
              Print Confirmation
            </Button>
            <Button onClick={onNewBooking} className="gap-2">
              Book Another Stay
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t py-8 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>
            Questions about your booking? Contact us at support@stayfinder.com
          </p>
          <p className="mt-2">© 2026 StayFinder. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

