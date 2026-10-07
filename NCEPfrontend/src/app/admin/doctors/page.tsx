import { redirect } from "next/navigation";

export default function AdminDoctorsPage() {
  redirect("/admin/users?tab=doctors");
}
