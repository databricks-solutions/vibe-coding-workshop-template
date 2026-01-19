import type { Listing, Review } from "@/types";

export const mockListings: Listing[] = [
  {
    id: "1",
    title: "Cozy Mountain Cabin with Stunning Views",
    description:
      "Escape to this charming cabin nestled in the mountains. Perfect for a peaceful getaway with breathtaking views of the valley below. Features a wrap-around deck, hot tub, and fully equipped kitchen. Just 15 minutes from downtown but feels like a world away.",
    location: {
      city: "Lake Tahoe",
      state: "CA",
      neighborhood: "Tahoe City",
      coordinates: { lat: 39.1633, lng: -120.1422 },
    },
    propertyType: "cabin",
    images: [
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
    ],
    pricePerNight: 245,
    cleaningFee: 85,
    serviceFee: 45,
    taxRate: 0.1,
    maxGuests: 6,
    bedrooms: 2,
    beds: 3,
    bathrooms: 2,
    amenities: [
      "Wifi",
      "Kitchen",
      "Free parking",
      "Hot tub",
      "Fireplace",
      "Mountain view",
      "Heating",
      "Coffee maker",
      "BBQ grill",
    ],
    rating: 4.92,
    reviewCount: 128,
    host: {
      name: "Sarah",
      responseRate: 98,
      superhost: true,
    },
    houseRules: {
      checkIn: "3:00 PM",
      checkOut: "11:00 AM",
      policies: [
        "No smoking",
        "No parties or events",
        "Pets allowed with approval",
      ],
    },
    cancellationPolicy: "moderate",
  },
  {
    id: "2",
    title: "Modern Downtown Loft with City Skyline",
    description:
      "Stylish loft in the heart of downtown with floor-to-ceiling windows offering panoramic city views. Walk to restaurants, shops, and entertainment. Features designer furnishings, smart home technology, and a fully stocked kitchen.",
    location: {
      city: "Austin",
      state: "TX",
      neighborhood: "Downtown",
      coordinates: { lat: 30.2672, lng: -97.7431 },
    },
    propertyType: "apartment",
    images: [
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
    ],
    pricePerNight: 189,
    cleaningFee: 65,
    serviceFee: 35,
    taxRate: 0.08,
    maxGuests: 4,
    bedrooms: 1,
    beds: 1,
    bathrooms: 1,
    amenities: [
      "Wifi",
      "Kitchen",
      "Gym",
      "Pool",
      "Air conditioning",
      "City view",
      "Workspace",
      "Doorman",
      "Elevator",
    ],
    rating: 4.87,
    reviewCount: 256,
    host: {
      name: "Michael",
      responseRate: 100,
      superhost: true,
    },
    houseRules: {
      checkIn: "4:00 PM",
      checkOut: "10:00 AM",
      policies: ["No smoking", "No pets", "Quiet hours after 10 PM"],
    },
    cancellationPolicy: "flexible",
  },
  {
    id: "3",
    title: "Beachfront Villa with Private Pool",
    description:
      "Wake up to the sound of waves at this stunning beachfront villa. Features a private infinity pool overlooking the ocean, outdoor living spaces, and direct beach access. Perfect for families or groups seeking a luxurious beach retreat.",
    location: {
      city: "San Diego",
      state: "CA",
      neighborhood: "La Jolla",
      coordinates: { lat: 32.8328, lng: -117.2713 },
    },
    propertyType: "villa",
    images: [
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
    ],
    pricePerNight: 495,
    cleaningFee: 150,
    serviceFee: 85,
    taxRate: 0.11,
    maxGuests: 10,
    bedrooms: 4,
    beds: 5,
    bathrooms: 3,
    amenities: [
      "Wifi",
      "Kitchen",
      "Free parking",
      "Private pool",
      "Beach access",
      "Ocean view",
      "Air conditioning",
      "BBQ grill",
      "Outdoor shower",
    ],
    rating: 4.96,
    reviewCount: 89,
    host: {
      name: "Jennifer",
      responseRate: 95,
      superhost: true,
    },
    houseRules: {
      checkIn: "4:00 PM",
      checkOut: "11:00 AM",
      policies: [
        "No smoking indoors",
        "No parties over 10 guests",
        "Pets allowed",
      ],
    },
    cancellationPolicy: "strict",
  },
  {
    id: "4",
    title: "Charming Historic Brownstone",
    description:
      "Experience city living in this beautifully restored 1890s brownstone. Original hardwood floors and exposed brick meet modern amenities. Located in a tree-lined neighborhood with easy access to public transit and local cafes.",
    location: {
      city: "Boston",
      state: "MA",
      neighborhood: "Back Bay",
      coordinates: { lat: 42.3503, lng: -71.0803 },
    },
    propertyType: "house",
    images: [
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
    ],
    pricePerNight: 275,
    cleaningFee: 95,
    serviceFee: 50,
    taxRate: 0.0625,
    maxGuests: 6,
    bedrooms: 3,
    beds: 4,
    bathrooms: 2,
    amenities: [
      "Wifi",
      "Kitchen",
      "Washer/Dryer",
      "Fireplace",
      "Garden access",
      "Heating",
      "Workspace",
      "Books & games",
    ],
    rating: 4.89,
    reviewCount: 167,
    host: {
      name: "David",
      responseRate: 92,
      superhost: false,
    },
    houseRules: {
      checkIn: "3:00 PM",
      checkOut: "11:00 AM",
      policies: ["No smoking", "No pets", "Please remove shoes indoors"],
    },
    cancellationPolicy: "moderate",
  },
  {
    id: "5",
    title: "Luxury High-Rise Condo with Amenities",
    description:
      "Live like a local in this sophisticated high-rise condo with resort-style amenities. Features modern finishes, a chef's kitchen, and access to rooftop pool, fitness center, and concierge services.",
    location: {
      city: "Miami",
      state: "FL",
      neighborhood: "Brickell",
      coordinates: { lat: 25.7617, lng: -80.1918 },
    },
    propertyType: "condo",
    images: [
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
    ],
    pricePerNight: 325,
    cleaningFee: 100,
    serviceFee: 60,
    taxRate: 0.13,
    maxGuests: 4,
    bedrooms: 2,
    beds: 2,
    bathrooms: 2,
    amenities: [
      "Wifi",
      "Kitchen",
      "Rooftop pool",
      "Gym",
      "Concierge",
      "City view",
      "Air conditioning",
      "Parking garage",
      "Security",
    ],
    rating: 4.91,
    reviewCount: 203,
    host: {
      name: "Alexandra",
      responseRate: 99,
      superhost: true,
    },
    houseRules: {
      checkIn: "4:00 PM",
      checkOut: "10:00 AM",
      policies: [
        "No smoking",
        "No parties",
        "Building quiet hours 11 PM - 7 AM",
      ],
    },
    cancellationPolicy: "flexible",
  },
  {
    id: "6",
    title: "Rustic Ranch House on 5 Acres",
    description:
      "Disconnect and unwind at this peaceful ranch property. Enjoy wide open spaces, stargazing, and authentic country living. Features a spacious porch, fire pit, and modern comforts inside a rustic exterior.",
    location: {
      city: "Fredericksburg",
      state: "TX",
      neighborhood: "Hill Country",
      coordinates: { lat: 30.2746, lng: -98.8719 },
    },
    propertyType: "house",
    images: [
      "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=800",
      "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
    ],
    pricePerNight: 195,
    cleaningFee: 75,
    serviceFee: 38,
    taxRate: 0.0825,
    maxGuests: 8,
    bedrooms: 3,
    beds: 5,
    bathrooms: 2,
    amenities: [
      "Wifi",
      "Kitchen",
      "Free parking",
      "Fire pit",
      "BBQ grill",
      "Porch",
      "Air conditioning",
      "Washer/Dryer",
      "Board games",
    ],
    rating: 4.94,
    reviewCount: 76,
    host: {
      name: "Robert",
      responseRate: 88,
      superhost: false,
    },
    houseRules: {
      checkIn: "2:00 PM",
      checkOut: "11:00 AM",
      policies: ["No smoking indoors", "Pets welcome", "Respect wildlife"],
    },
    cancellationPolicy: "moderate",
  },
];

export const mockReviews: Record<string, Review[]> = {
  "1": [
    {
      id: "r1",
      author: "Emily R.",
      date: "December 2025",
      rating: 5,
      comment:
        "Absolutely magical! The views from the deck are breathtaking and the hot tub under the stars was incredible. Sarah was very responsive and the cabin had everything we needed.",
    },
    {
      id: "r2",
      author: "James T.",
      date: "November 2025",
      rating: 5,
      comment:
        "Perfect mountain getaway. The cabin is cozy, clean, and well-stocked. We loved making breakfast in the kitchen and relaxing by the fireplace. Will definitely return!",
    },
    {
      id: "r3",
      author: "Maria S.",
      date: "October 2025",
      rating: 4,
      comment:
        "Beautiful property and great location. Only minor issue was the wifi was a bit spotty, but honestly it was nice to disconnect. Highly recommend!",
    },
  ],
  "2": [
    {
      id: "r4",
      author: "Chris P.",
      date: "January 2026",
      rating: 5,
      comment:
        "Best downtown location you could ask for. The loft is stunning and the views are even better in person. Walking distance to everything!",
    },
    {
      id: "r5",
      author: "Amanda K.",
      date: "December 2025",
      rating: 5,
      comment:
        "Michael is an amazing host. The space is exactly as pictured - modern, clean, and comfortable. The building amenities were a nice bonus.",
    },
  ],
};

export function searchListings(filters: {
  location?: string;
  guests?: number;
  priceMax?: number;
}): Listing[] {
  let results = [...mockListings];

  if (filters.location) {
    const searchTerm = filters.location.toLowerCase();
    results = results.filter(
      (listing) =>
        listing.location.city.toLowerCase().includes(searchTerm) ||
        listing.location.state.toLowerCase().includes(searchTerm) ||
        listing.location.neighborhood.toLowerCase().includes(searchTerm)
    );
  }

  if (filters.guests) {
    results = results.filter((listing) => listing.maxGuests >= filters.guests!);
  }

  if (filters.priceMax) {
    results = results.filter(
      (listing) => listing.pricePerNight <= filters.priceMax!
    );
  }

  return results;
}

export function getListingById(id: string): Listing | undefined {
  return mockListings.find((listing) => listing.id === id);
}

export function getReviewsForListing(listingId: string): Review[] {
  return mockReviews[listingId] || [];
}

