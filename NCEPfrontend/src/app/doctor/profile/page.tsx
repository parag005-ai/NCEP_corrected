import { PageHeader } from "@/components/layout/PageHeader";
import { ProfileForm } from "@/components/profile/ProfileForm";

export default function DoctorProfilePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="My Profile"
        description="Manage your professional details and account preferences."
      />
      <ProfileForm />
    </div>
  );
}
