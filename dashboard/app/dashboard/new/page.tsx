"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function NewRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/search?mode=apply"); }, [router]);
  return null;
}
