import ClientPage from './ClientPage';

export default async function Page({ params }: { params: Promise<{ reportId: string }> }) {
  return <ClientPage params={params} />;
}
