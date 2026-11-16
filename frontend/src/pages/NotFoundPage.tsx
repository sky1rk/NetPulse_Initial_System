import { Link } from "react-router-dom";

import { EmptyState, PageHeader } from "../components/ui";

export default function NotFoundPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Page not found" description="The requested route does not exist in this NetPulse build." />
      <EmptyState
        title="Nothing is mapped here"
        description="Use the navigation to open Overview, Discovery, Devices, Analytics, Security, Diagnostics, Reports, Topology or Settings."
        action={
          <Link to="/" className="btn-primary">
            Return to overview
          </Link>
        }
      />
    </div>
  );
}
