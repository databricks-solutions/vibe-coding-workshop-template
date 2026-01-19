import { Star, MapPin, Users, Bed, Bath } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import type { Listing } from "@/types";

interface ListingCardProps {
  listing: Listing;
  onClick: (id: string) => void;
}

export function ListingCard({ listing, onClick }: ListingCardProps) {
  return (
    <Card
      className="overflow-hidden cursor-pointer group hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
      onClick={() => onClick(listing.id)}
    >
      {/* Image */}
      <div className="relative aspect-[4/3] overflow-hidden">
        <img
          src={listing.images[0]}
          alt={listing.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        {listing.host.superhost && (
          <Badge className="absolute top-3 left-3 bg-white text-black shadow-md">
            ⭐ Superhost
          </Badge>
        )}
        <div className="absolute bottom-3 right-3 bg-black/70 text-white px-2 py-1 rounded text-sm font-semibold">
          {formatCurrency(listing.pricePerNight)}/night
        </div>
      </div>

      <CardContent className="p-4">
        {/* Rating and location */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="h-3 w-3" />
            {listing.location.city}, {listing.location.state}
          </div>
          <div className="flex items-center gap-1">
            <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
            <span className="font-semibold">{listing.rating}</span>
            <span className="text-muted-foreground text-sm">
              ({listing.reviewCount})
            </span>
          </div>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-lg line-clamp-1 mb-2 group-hover:text-primary transition-colors">
          {listing.title}
        </h3>

        {/* Property details */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            {listing.maxGuests}
          </div>
          <div className="flex items-center gap-1">
            <Bed className="h-4 w-4" />
            {listing.bedrooms} bed{listing.bedrooms > 1 ? "s" : ""}
          </div>
          <div className="flex items-center gap-1">
            <Bath className="h-4 w-4" />
            {listing.bathrooms} bath{listing.bathrooms > 1 ? "s" : ""}
          </div>
        </div>

        {/* Key amenities */}
        <div className="flex flex-wrap gap-1">
          {listing.amenities.slice(0, 3).map((amenity) => (
            <Badge key={amenity} variant="secondary" className="text-xs">
              {amenity}
            </Badge>
          ))}
          {listing.amenities.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{listing.amenities.length - 3} more
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

