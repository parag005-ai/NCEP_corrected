import { Suspense } from "react";
import AdminEditor from "./AdminEditor";

export default function EditAdministratorPage() {
  return (
    <Suspense fallback={null}>
      <AdminEditor />
    </Suspense>
  );
}
