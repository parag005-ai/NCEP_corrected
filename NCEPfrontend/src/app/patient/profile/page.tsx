import { PageHeader } from "@/components/layout/PageHeader";
import { ProfileForm } from "@/components/profile/ProfileForm";

export default function PatientProfilePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="My Profile"
        description="Manage your personal details and account preferences."
      />
      <ProfileForm />
    </div>
  );
}
