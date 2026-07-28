import type { Metadata } from "next";
import { GuestEstimateView } from "@/components/guest-estimate";

export const metadata: Metadata = {
  title: "Private repair request | MyCasaPro",
  description: "Review a homeowner's repair request and send an estimate.",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default async function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <GuestEstimateView token={token} />;
}
