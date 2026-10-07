import ClientPage from './ClientPage';

export default async function Page({ params }: { params: Promise<{ patientId: string }> }) {
  return <ClientPage params={params} />;
}
