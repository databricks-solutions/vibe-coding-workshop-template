import {
  ArrowLeft,
  Star,
  MapPin,
  Users,
  Bed,
  Bath,
  Home,
  Shield,
  Award,
  Clock,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookingWidget } from "@/components/booking/BookingWidget";
import { getListingById, getReviewsForListing } from "@/data/mockListings";
import type { PricingBreakdown } from "@/types";

interface ListingDetailPageProps {
  listingId: string;
  onBack: () => void;
  onReserve: (
    listingId: string,
    checkIn: Date,
    checkOut: Date,
    guests: number,
    pricing: PricingBreakdown
  ) => void;
}

export function ListingDetailPage({
  listingId,
  onBack,
  onReserve,
}: ListingDetailPageProps) {
  const listing = getListingById(listingId);
  const reviews = getReviewsForListing(listingId);
  const [showGallery, setShowGallery] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

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

  const handleReserve = (
    checkIn: Date,
    checkOut: Date,
    guests: number,
    pricing: PricingBreakdown
  ) => {
    onReserve(listingId, checkIn, checkOut, guests, pricing);
  };

  const nextImage = () => {
    setCurrentImageIndex((prev) => (prev + 1) % listing.images.length);
  };

  const prevImage = () => {
    setCurrentImageIndex(
      (prev) => (prev - 1 + listing.images.length) % listing.images.length
    );
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Button variant="ghost" onClick={onBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to search
          </Button>
        </div>
      </div>

      {/* Image Gallery */}
      <div className="container mx-auto px-4 py-6">
        <div
          className="grid grid-cols-4 grid-rows-2 gap-2 h-[400px] rounded-xl overflow-hidden cursor-pointer"
          onClick={() => setShowGallery(true)}
        >
          <div className="col-span-2 row-span-2">
            <img
              src={listing.images[0]}
              alt={listing.title}
              className="w-full h-full object-cover hover:opacity-90 transition-opacity"
            />
          </div>
          {listing.images.slice(1, 5).map((image, index) => (
            <div key={index} className="overflow-hidden">
              <img
                src={image}
                alt={`${listing.title} ${index + 2}`}
                className="w-full h-full object-cover hover:opacity-90 transition-opacity"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Full Gallery Modal */}
      {showGallery && (
        <div className="fixed inset-0 bg-black z-50 flex items-center justify-center">
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 right-4 text-white hover:bg-white/20"
            onClick={() => setShowGallery(false)}
          >
            <X className="h-6 w-6" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-4 text-white hover:bg-white/20"
            onClick={prevImage}
          >
            <ChevronLeft className="h-8 w-8" />
          </Button>
          <img
            src={listing.images[currentImageIndex]}
            alt={listing.title}
            className="max-h-[90vh] max-w-[90vw] object-contain"
          />
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 text-white hover:bg-white/20"
            onClick={nextImage}
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
          <div className="absolute bottom-4 text-white text-sm">
            {currentImageIndex + 1} / {listing.images.length}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="container mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Details */}
          <div className="lg:col-span-2 space-y-8">
            {/* Title and basics */}
            <div>
              <h1 className="text-3xl font-bold mb-2">{listing.title}</h1>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  <span className="font-semibold">{listing.rating}</span>
                  <span className="text-muted-foreground">
                    · {listing.reviewCount} reviews
                  </span>
                </div>
                {listing.host.superhost && (
                  <Badge variant="secondary">
                    <Award className="h-3 w-3 mr-1" />
                    Superhost
                  </Badge>
                )}
                <div className="flex items-center gap-1 text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  {listing.location.neighborhood}, {listing.location.city},{" "}
                  {listing.location.state}
                </div>
              </div>
            </div>

            {/* Property highlights */}
            <div className="flex items-center gap-6 py-6 border-y">
              <div className="flex items-center gap-3">
                <Home className="h-6 w-6" />
                <div>
                  <p className="font-medium capitalize">{listing.propertyType}</p>
                  <p className="text-sm text-muted-foreground">
                    Hosted by {listing.host.name}
                  </p>
                </div>
              </div>
              <div className="h-10 w-px bg-border" />
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-muted-foreground" />
                <span>{listing.maxGuests} guests</span>
              </div>
              <div className="flex items-center gap-2">
                <Bed className="h-5 w-5 text-muted-foreground" />
                <span>{listing.bedrooms} bedrooms</span>
              </div>
              <div className="flex items-center gap-2">
                <Bath className="h-5 w-5 text-muted-foreground" />
                <span>{listing.bathrooms} baths</span>
              </div>
            </div>

            {/* Description */}
            <div>
              <h2 className="text-xl font-semibold mb-4">About this place</h2>
              <p className="text-muted-foreground leading-relaxed">
                {listing.description}
              </p>
            </div>

            {/* Amenities */}
            <Card>
              <CardHeader>
                <CardTitle>What this place offers</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {listing.amenities.map((amenity) => (
                    <div key={amenity} className="flex items-center gap-3">
                      <div className="h-6 w-6 rounded bg-gray-100 flex items-center justify-center text-xs">
                        ✓
                      </div>
                      <span>{amenity}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* House Rules */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  House Rules
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Check-in</p>
                    <p className="font-medium">{listing.houseRules.checkIn}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Check-out</p>
                    <p className="font-medium">{listing.houseRules.checkOut}</p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Policies</p>
                  <ul className="space-y-1">
                    {listing.houseRules.policies.map((policy, index) => (
                      <li key={index} className="flex items-center gap-2">
                        <span className="text-muted-foreground">•</span>
                        {policy}
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Reviews */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
                  {listing.rating} · {listing.reviewCount} reviews
                </CardTitle>
              </CardHeader>
              <CardContent>
                {reviews.length > 0 ? (
                  <div className="space-y-6">
                    {reviews.map((review) => (
                      <div key={review.id} className="border-b last:border-0 pb-4 last:pb-0">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center font-semibold">
                            {review.author.charAt(0)}
                          </div>
                          <div>
                            <p className="font-medium">{review.author}</p>
                            <p className="text-sm text-muted-foreground">
                              {review.date}
                            </p>
                          </div>
                        </div>
                        <p className="text-muted-foreground">{review.comment}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">
                    No reviews yet. Be the first to stay here!
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Cancellation Policy */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Cancellation Policy
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Badge className="mb-2 capitalize">
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
          </div>

          {/* Right Column - Booking Widget */}
          <div className="lg:col-span-1">
            <BookingWidget listing={listing} onReserve={handleReserve} />
          </div>
        </div>
      </div>
    </div>
  );
}

