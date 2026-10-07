import { PageHeader } from "@/components/layout/PageHeader";
import { ProfileForm } from "@/components/profile/ProfileForm";

export default function AdminProfilePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="My Profile"
        description="Manage your administrative details and account preferences."
      />
      <ProfileForm />
    </div>
  );
}
