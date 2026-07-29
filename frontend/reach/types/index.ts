//for shared types, anything that is used in more than one file goes here.

export interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
}

export interface NominatimReverseResult {
  place_id: number;
  osm_type: string;
  osm_id: number;
  lat: string;
  lon: string;
  display_name: string;
  address?: {
    house_number?: string;
    road?: string;
    neighbourhood?: string;
    suburb?: string;
    city?: string;
    town?: string;
    village?: string;
    county?: string;
    state?: string;
    postcode?: string;
    country?: string;
    country_code?: string;
  };
  boundingbox: [string, string, string, string];
}

export interface FeedItem {
  id: string;
  title: string;
  subtitle: string;
  price: string;
  imageSrc: string;
}

export type IconWeight =
  | "thin"
  | "light"
  | "regular"
  | "bold"
  | "fill"
  | "duotone";


export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  bio: string | null;
  phone_number: string | null;
  profile_picture: string | null;
  is_email_verified: boolean;
  created_at: string;
};

export type PublicUser = {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  bio: string | null;
  profile_picture: string | null;
};